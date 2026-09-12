"""Turn text into vectors (embeddings) with a local, open-source model.

Runs on your own machine -> free and private, no per-token cost.
To switch models later (e.g. Ollama, or a hosted API), you only change THIS class -
nothing else in the app moves. That is the point of keeping it separate.
"""


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None  # loaded lazily on first use

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts):
        """texts: a single string OR a list of strings.
        Returns one vector, or a list of vectors. Vectors are normalized, so a
        dot product between two of them IS their cosine similarity."""
        single = isinstance(texts, str)
        vecs = self._load().encode(
            [texts] if single else list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs[0] if single else vecs
