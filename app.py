"""Streamlit chat UI (repo-root entry; runs on Streamlit Community Cloud or locally)."""
import streamlit as st

from src.analytics import log, summarize
from src.bm25 import BM25
from src.chunking import chunk_documents
from src.config import load_config
from src.customers import identify, load_customers, profile_prompt
from src.embed import Embedder
from src.generate import answer, recommend
from src.loaders import load_markdown_dir
from src.persist import delete, load_all, save
from src.recommend import embed_catalog, load_catalog, recommend_products
from src.retrieve import retrieve
from src.schema import Document
from src.scrape import fetch_text
from src import shopify
import chat  # shared ask(): greeting/small-talk + retrieval + failure logging


@st.cache_resource
def build():
    cfg = load_config()
    docs = load_markdown_dir(cfg["corpus_dir"])
    chunks = chunk_documents(docs)
    embedder = Embedder(cfg["model"]["embed"])
    vecs = embedder.embed([c.text for c in chunks])
    bm25 = BM25([c.text for c in chunks])
    persona = open(cfg["persona_file"], encoding="utf-8").read()
    if shopify.configured(cfg):
        catalog = shopify.fetch_catalog(cfg)
        customers = shopify.fetch_customers(cfg)
    else:
        catalog = load_catalog(cfg.get("catalog_file"))
        customers = load_customers(cfg.get("customers_file"))
    catalog_vecs = embed_catalog(catalog, embedder)
    return cfg, chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers


def make_persona(name, voice):
    base = "You are a friendly assistant" + (f" called {name}" if name else "") + ". Answer questions from the user's own content only."
    if voice:
        base += f"\n\nHow to talk:\n- {voice}\n- Warm, short sentences."
    base += "\n\nRules:\n- Answer only from the context you are given. If it is not there, say you do not know and offer a human."
    return base


cfg, chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers = build()
ui = cfg.get("ui", {})
# On Streamlit Cloud the OpenAI-compatible key is set as a dashboard secret.
try:
    api_key = st.secrets.get("OPENROUTER_API_KEY", None)
except Exception:
    # No secrets.toml on self-hosted runs; the key is read from OPENROUTER_API_KEY env by the engine.
    api_key = None

st.set_page_config(page_title=ui.get("title", "Ana"), page_icon=ui.get("emoji", "🤍"))

# right-to-left layout for Arabic clients
if cfg.get("language") == "ar":
    st.markdown(
        '<style>div[data-testid="stAppViewContainer"] {direction: rtl; text-align: right;}</style>',
        unsafe_allow_html=True,
    )

page = st.sidebar.radio("View", ["Chat", "Usage", "Build"])

if page == "Usage":
    m = summarize(cfg["analytics_log"])
    st.title("Usage")
    c1, c2, c3 = st.columns(3)
    c1.metric("Questions", m["total"])
    c2.metric("Answered", m["answered"])
    c3.metric("Deflected", m["deflected"])
    st.caption(f"Deflection rate: {m['deflection_rate']:.0%}")
    if m["top_sources"]:
        st.subheader("Top sources")
        for src, n in m["top_sources"]:
            st.text(f"{src}  ·  {n}")
    if m["recent"]:
        st.subheader("Recent")
        for e in reversed(m["recent"]):
            flag = "answered" if e.get("answered") else "deflected"
            st.text(f"[{flag}]  {e.get('question', '')}")

elif page == "Build":
    st.title("Build your assistant")
    st.caption("Paste content or upload files, give it a voice, then save and use it.")

    built_path = cfg.get("built_path")
    saved = load_all(built_path)

    st.subheader("New assistant")
    with st.form("onboard"):
        name = st.text_input("Name", placeholder="e.g. Glow Guide")
        url = st.text_input("Or paste a website URL", placeholder="https://yourstore.com")
        uploaded = st.file_uploader("Upload files (.md / .txt)", type=["md", "txt"], accept_multiple_files=True)
        content = st.text_area(
            "Or paste content", height=180,
            placeholder="Paste your shipping, returns, products, FAQ, anything. A blank line between topics works best.",
        )
        voice = st.text_area("Voice (optional)", height=70, placeholder="Warm best friend, short sentences")
        submitted = st.form_submit_button("Build and save")

    if submitted:
        parts = []
        if url.strip():
            scraped = fetch_text(url.strip())
            if scraped:
                parts.append(scraped)
            else:
                st.warning(f"Could not read {url.strip()}. Paste content or upload a file instead.")
        if content.strip():
            parts.append(content.strip())
        if uploaded:
            parts += [f.read().decode("utf-8", errors="ignore") for f in uploaded]
        text = "\n\n".join(p.strip() for p in parts if p.strip())
        if not text.strip():
            st.warning("Give me a URL, some pasted text, or a file to work with.")
        else:
            save(built_path, name.strip() or "Assistant", text.strip(), voice.strip())
            st.success("Saved. Select it below to chat.")
            st.rerun()

    if saved:
        st.subheader("Your assistants")
        sel = st.selectbox("Select an assistant", range(len(saved)), format_func=lambda i: saved[i]["name"])
        a = saved[sel]
        ckey = (sel, a["content"])
        if st.session_state.get("built_key") != ckey:
            doc = Document(id="custom", text=a["content"], source="your-content")
            bchunks = chunk_documents([doc])
            bvecs = embedder.embed([c.text for c in bchunks])
            st.session_state.built_key = ckey
            st.session_state.built = {
                "name": a["name"],
                "chunks": bchunks,
                "vecs": bvecs,
                "persona": make_persona(a["name"], a.get("voice", "")),
            }
            st.session_state.built_msgs = []

        b = st.session_state.built
        if st.button("Delete this assistant", key=f"del_{sel}"):
            delete(built_path, sel)
            st.session_state.pop("built_key", None)
            st.rerun()

        for m_ in st.session_state.built_msgs:
            with st.chat_message(m_["role"]):
                st.markdown(m_["content"])
        if q := st.chat_input("Ask this assistant…", key="built_chat"):
            st.session_state.built_msgs.append({"role": "user", "content": q})
            with st.chat_message("user"):
                st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("…"):
                    qv = embedder.embed([q])[0]
                    hits = retrieve(q, qv, b["vecs"], b["chunks"], top_k=4)
                    threshold = cfg["retrieval"].get("threshold")
                    a_out = answer(q, hits, b["persona"], cfg["model"]["generate"], max_tokens=250, threshold=threshold, api_key=api_key)
                st.markdown(a_out)
            st.session_state.built_msgs.append({"role": "assistant", "content": a_out})
    else:
        st.info("Nothing saved yet. Build your first assistant above.")

else:
    st.title(ui.get("title", "Ana"))
    st.caption(ui.get("subtitle", ""))

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m_ in st.session_state.messages:
        with st.chat_message(m_["role"]):
            st.markdown(m_["content"])

    if prompt := st.chat_input(ui.get("placeholder", "Ask…")):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("…"):
                a = chat.ask(
                    chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs,
                    customers, cfg, prompt, api_key=api_key,
                )
            st.markdown(a)
        st.session_state.messages.append({"role": "assistant", "content": a})