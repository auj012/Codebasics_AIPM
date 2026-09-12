"""Codebasics Digital Asset Assistant - the search screen.

Run it with:  streamlit run streamlit_app.py
(Build the index first:  python build_index.py)
"""
import json
from pathlib import Path

import numpy as np
import streamlit as st

from assistant.models import Asset
from assistant.embedder import Embedder
from assistant.vector_store import VectorStore
from assistant.guardrails import Guardrails
from assistant.search_engine import SearchEngine
from assistant.locate import locate_in_file, locate_in_transcript


def yt_jump(url, sec):
    """Build a YouTube URL that opens at `sec` seconds."""
    if "watch?v=" in url:
        return f"{url}&t={sec}s"
    if "youtu.be/" in url:
        return f"{url}{'&' if '?' in url else '?'}t={sec}"
    return url

BASE = Path(__file__).resolve().parent.parent
INDEX = BASE / "index"


@st.cache_resource
def load_engine():
    """Load the index once and build the search engine (cached across reruns)."""
    catalog = json.load(open(INDEX / "catalog.json", encoding="utf-8"))
    assets = [Asset(**d) for d in catalog]
    embeddings = np.load(INDEX / "embeddings.npy")
    store = VectorStore()
    store.add_all(assets, embeddings)
    return SearchEngine(store, Embedder(), Guardrails())


@st.cache_data
def load_transcripts():
    p = INDEX / "transcripts.json"
    return json.load(open(p, encoding="utf-8")) if p.exists() else {}


st.set_page_config(page_title="Codebasics Digital Asset Assistant", page_icon="🔍")
st.title("🔍 Codebasics Digital Asset Assistant")
st.caption("Find your assets by meaning - decks, PDFs, thumbnails, and videos - not by filename.")

if not (INDEX / "catalog.json").exists():
    st.error("No index found. Run  `python build_index.py`  first, then reload.")
    st.stop()

engine = load_engine()
transcripts = load_transcripts()

query = st.text_input("What are you looking for?", placeholder="e.g. power bi thumbnail")

if query:
    out = engine.search(query, k=5)

    if out["status"] in ("blocked", "no_match"):
        st.warning(out["message"])
    else:
        if out["status"] == "low_confidence":
            st.info("Low confidence - try refining your search.")
        st.write(f"**{len(out['results'])} result(s):**")
        for r in out["results"]:
            with st.container(border=True):
                st.markdown(f"**{r.asset.name}**  ·  _{r.asset.type}_  ·  match {r.score:.2f}")
                loc = r.asset.location
                if str(loc).startswith("http"):
                    # published link -> open it (YouTube jumps to the matching moment)
                    label, jump = "Open link", loc
                    if r.asset.type == "youtube":
                        segs = transcripts.get(str(r.asset.id))
                        if segs:
                            sec, snip = locate_in_transcript(segs, query)
                            if sec is not None:
                                jump = yt_jump(loc, sec)
                                label = f"▶ Open at {sec // 60}:{sec % 60:02d}"
                    st.markdown(f"🔗 [{label}]({jump})")
                else:
                    # local file -> full path, where-in-file, and a download button
                    # normalize Windows backslashes so paths resolve on Linux (cloud) too
                    abs_path = BASE / str(loc).replace("\\", "/")
                    st.caption(f"📁 {abs_path}")
                    if r.asset.type in ("deck", "pdf"):
                        where, snip = locate_in_file(abs_path, query)
                        if where:
                            st.caption(f"📄 Found on: **{where}**")
                    try:
                        with open(abs_path, "rb") as fh:
                            st.download_button("⬇ Download", fh.read(),
                                               file_name=r.asset.name,
                                               key=f"dl_{r.asset.id}")
                    except Exception:
                        st.caption("⚠ File not available in this build.")
                if r.asset.modified:
                    st.caption(f"🗓 {r.asset.modified}")
                if r.matched_snippet:
                    st.caption(f"matched: {r.matched_snippet}")
