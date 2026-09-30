"""Streamlit chat UI for the reusable assistant."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

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
    persona = open(cfg["persona_file"], encoding="utf-8").read()
    return cfg, chunks, vecs, embedder, persona


cfg, chunks, vecs, embedder, persona = build()
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
            hits = retrieve(qv, vecs, chunks, cfg["retrieval"]["top_k"])
            a = answer(prompt, [d for d, _ in hits], persona, cfg["model"]["generate"], cfg.get("max_tokens", 250))
        st.markdown(a)
    st.session_state.messages.append({"role": "assistant", "content": a})