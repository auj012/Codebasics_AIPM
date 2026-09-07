"""Run this ONCE to build the search index.

    python build_index.py

It reads the sample assets, fetches YouTube transcripts, embeds everything,
and writes index/catalog.json + index/embeddings.npy. Re-run it whenever assets
change (nightly, in production).
"""
from pathlib import Path

from assistant.embedder import Embedder
from assistant.indexer import AssetIndexer

BASE = Path(__file__).parent

if __name__ == "__main__":
    print("Building the index - reading files, fetching transcripts, embedding...")
    n = AssetIndexer(BASE, Embedder()).build(BASE / "index")
    print(f"Done. Indexed {n} assets -> {BASE / 'index'}")
