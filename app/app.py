"""Streamlit chat UI for the reusable assistant."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.bm25 import BM25
from src.chunking import chunk_documents
from src.config import load_config
from src.embed import Embedder
from src.generate import answer
from src.loaders import load_markdown_dir
from src.retrieve import retrieve


@st.cache_resource
def build():
    cfg = load_config()
    docs = load_markdown_dir(cfg["corpus_dir"])
    chunks = chunk_documents(docs)
    embedder = Embedder(cfg["model"]["embed"])
    vecs = embedder.embed([c.text for c in chunks])
    bm25 = BM25([c.text for c in chunks])
    persona = open(cfg["persona_file"], encoding="utf-8").read()
    return cfg, chunks, vecs, bm25, embedder, persona


cfg, chunks, vecs, bm25, embedder, persona = build()
ui = cfg.get("ui", {})

st.set_page_config(page_title=ui.get("title", "Ask"), page_icon=ui.get("emoji", "🤍"))
st.title(ui.get("title", "Ask"))
st.caption(ui.get("subtitle", ""))

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input(ui.get("placeholder", "Ask…")):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("…"):
            qv = embedder.embed([prompt])[0]
            use_hybrid = cfg["retrieval"].get("hybrid", False)
            hits = retrieve(prompt, qv, vecs, chunks, bm25=bm25 if use_hybrid else None, top_k=cfg["retrieval"]["top_k"])
            a = answer(
                prompt, hits, persona, cfg["model"]["generate"],
                max_tokens=cfg.get("max_tokens", 250),
                threshold=cfg["retrieval"].get("threshold"),
            )
        st.markdown(a)
    st.session_state.messages.append({"role": "assistant", "content": a})