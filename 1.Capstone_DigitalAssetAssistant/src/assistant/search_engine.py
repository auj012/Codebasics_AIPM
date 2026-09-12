"""THE HEART OF THE PRODUCT.

A query comes in; this turns it into ranked results:
    query -> guardrails -> embed -> vector search -> rank (relevance, then recency)

Read this file closely - it is the piece you will explain in your demo.
"""
from .models import SearchResult


class SearchEngine:
    def __init__(self, store, embedder, guardrails, threshold=0.25):
        self.store = store
        self.embedder = embedder
        self.guardrails = guardrails
        self.threshold = threshold  # below this = "no strong match"

    def search(self, query, k=5):
        # 1) Guardrails first (empty / too long / rate limit / non-English).
        ok, message = self.guardrails.check_query(query)
        if not ok:
            return {"status": "blocked", "message": message, "results": []}

        # 2) Turn the query into a vector and find the closest assets.
        query_vec = self.embedder.embed(query)
        hits = self.store.search(query_vec, k=k)  # [(asset, score), ...]

        # 3) Nothing clears the bar -> out-of-domain / no match (never fake a result).
        if not hits or hits[0][1] < self.threshold:
            msg = ("No matching asset found - this library holds Codebasics EdTech "
                   "content; try a related topic.")
            hint = self.guardrails.acronym_hint(query)
            if hint:
                msg = f"Did you mean '{hint}'? " + msg
            return {"status": "no_match", "message": msg, "results": []}

        # 4) Rank by relevance first, then recency (newest wins among close matches).
        hits = self._rank_by_relevance_then_recency(hits)

        results = [
            SearchResult(asset=a, score=s, matched_snippet=self._snippet(a))
            for a, s in hits
        ]
        low = hits[0][1] < (self.threshold + 0.15)
        return {"status": "low_confidence" if low else "ok", "message": "", "results": results}

    def _rank_by_relevance_then_recency(self, hits, close=0.05):
        """Sort by score; within a group of near-equal scores, newest date first."""
        hits = sorted(hits, key=lambda h: -h[1])
        ranked, i = [], 0
        while i < len(hits):
            j = i + 1
            while j < len(hits) and abs(hits[j][1] - hits[i][1]) <= close:
                j += 1
            group = sorted(hits[i:j], key=lambda h: h[0].modified or "", reverse=True)
            ranked.extend(group)
            i = j
        return ranked

    @staticmethod
    def _snippet(asset, n=140):
        text = (asset.text or "").strip()
        return (text[:n] + "...") if len(text) > n else text
