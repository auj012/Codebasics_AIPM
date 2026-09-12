"""Safety and scope checks - keeps the assistant on-topic, English-only, and
abuse-resistant. Straight from the PRD guardrails + FR list.
"""
import time
from pathlib import Path

# FR-7: only these file types are indexed/searched. Everything else is ignored.
SUPPORTED_EXT = {".pdf", ".pptx", ".ppt", ".png", ".jpg", ".jpeg"}

# FR-9: tiny acronym dictionary for disambiguation (v1).
ACRONYMS = {
    "ml": "Machine Learning", "ai": "Artificial Intelligence",
    "bi": "Business Intelligence", "da": "Data Analyst",
    "ds": "Data Science", "de": "Data Engineering",
    "genai": "Generative AI", "nlp": "Natural Language Processing",
}


class Guardrails:
    def __init__(self, max_query_len=200, rate_limit=20, window_sec=60):
        self.max_query_len = max_query_len
        self.rate_limit = rate_limit          # FR-10: queries allowed per window
        self.window_sec = window_sec
        self._times = []

    # ---- index-time: file allowlist (FR-7) ----
    @staticmethod
    def is_supported_file(path) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXT

    # ---- search-time: query checks ----
    def check_query(self, query):
        """Return (ok, message). When ok is False, message is shown to the user."""
        q = (query or "").strip()
        if not q:
            return False, "Please type something to search."
        if len(q) > self.max_query_len:
            return False, "That query is too long - please shorten it."
        if not self._within_rate_limit():
            return False, "Search limit reached - please wait a moment and try again."
        if not self._looks_english(q):
            return False, "This library is English-only - please search in English."
        return True, ""

    def _within_rate_limit(self) -> bool:
        now = time.time()
        self._times = [t for t in self._times if now - t < self.window_sec]
        if len(self._times) >= self.rate_limit:
            return False
        self._times.append(now)
        return True

    @staticmethod
    def _looks_english(q) -> bool:
        # Crude but effective: if too many letters are non-ASCII, treat as non-English.
        letters = [c for c in q if c.isalpha()]
        if not letters:
            return True
        ascii_letters = [c for c in letters if ord(c) < 128]
        return len(ascii_letters) / len(letters) >= 0.6

    @staticmethod
    def acronym_hint(query):
        """If the whole query is a known acronym, return its expansion, else None."""
        return ACRONYMS.get(query.strip().lower())
