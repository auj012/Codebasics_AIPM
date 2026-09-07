"""Holds all the asset vectors and finds the ones closest to a query vector.

v1 keeps everything in memory (a NumPy array) - perfect for the sample library.
To scale to thousands+, swap the internals for FAISS/Chroma without changing the
method names. That is the swappable design from the PRD scalability section.
"""
import numpy as np


class VectorStore:
    def __init__(self):
        self.assets = []      # list[Asset], same order as the rows of `matrix`
        self.matrix = None    # np.ndarray, shape (num_assets, vector_dim)

    def add_all(self, assets, embeddings):
        self.assets = list(assets)
        self.matrix = np.asarray(embeddings, dtype="float32")

    def search(self, query_vec, k=5):
        """Return the top-k [(asset, score)] by cosine similarity.
        Vectors are normalized, so cosine similarity is just the dot product."""
        if self.matrix is None or len(self.assets) == 0:
            return []
        scores = self.matrix @ np.asarray(query_vec, dtype="float32")
        top = np.argsort(-scores)[:k]
        return [(self.assets[i], float(scores[i])) for i in top]
