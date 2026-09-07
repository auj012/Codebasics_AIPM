"""Builds the searchable index ONCE (the heavy, offline step):

    walk the assets -> extract text -> fetch YouTube transcripts -> embed -> save

Saves two files into index/:
    catalog.json    - the list of assets (name, type, location, text, date)
    embeddings.npy  - the matching vectors

The app then just loads these and searches - fast and fully local.
"""
import json
import datetime
from pathlib import Path

import numpy as np

from .models import Asset
from .extractors import (PdfExtractor, PptxExtractor, ImageExtractor,
                         YouTubeTranscriptExtractor)
from .guardrails import Guardrails


class AssetIndexer:
    def __init__(self, base_dir, embedder):
        self.base = Path(base_dir)
        self.assets_dir = self.base / "Dataset" / "Dataset" / "Dataset" / "sample_assets" / "sample_assets"
        self.links_xlsx = self.base / "Dataset" / "Dataset" / "Dataset" / "public_links.xlsx"
        self.embedder = embedder
        self.pdf = PdfExtractor()
        self.pptx = PptxExtractor()
        self.img = ImageExtractor()
        self.yt = YouTubeTranscriptExtractor()

    def build(self, index_dir, fetch_transcripts=True):
        assets = []
        cid = 0

        # 1) Local files (only supported types - FR-7 allowlist).
        for path in sorted(self.assets_dir.rglob("*")):
            if not path.is_file() or not Guardrails.is_supported_file(path):
                continue
            ext = path.suffix.lower()
            if ext == ".pdf":
                inside, atype = self.pdf.extract(path), "pdf"
            elif ext in (".pptx", ".ppt"):
                inside, atype = self.pptx.extract(path), "deck"
            else:
                inside, atype = self.img.extract(path), "image"
            pretty = path.stem.replace("_", " ").replace("-", " ")
            cid += 1
            assets.append(Asset(
                id=cid, name=path.name, type=atype, source="local file",
                location=str(path.relative_to(self.base)),
                text=(pretty + ". " + inside).strip(),
                modified=datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d"),
            ))

        # 2) Public links from the spreadsheet (title + description are already text).
        # Transcript cache: once a video's transcript is fetched, it is saved here and
        # NEVER re-fetched - so rebuilds are instant and we never get re-blocked by YouTube.
        transcripts = {}  # asset_id -> [[start_seconds, text], ...]
        cache_path = Path(index_dir) / "transcript_cache.json"
        cache = json.load(open(cache_path, encoding="utf-8")) if cache_path.exists() else {}

        import openpyxl
        wb = openpyxl.load_workbook(str(self.links_xlsx), data_only=True)
        ws = wb.active
        for row in list(ws.iter_rows(values_only=True))[1:]:
            title, url, source_type = (list(row) + [None, None, None])[:3]
            if not title:
                continue
            stype = str(source_type or "link").strip().lower()
            text = str(title).strip()
            segs = []
            is_yt = "youtube" in stype or "youtu" in str(url)
            vid = self.yt._video_id(str(url)) if is_yt else ""
            if vid:
                if vid in cache:                       # already have it -> reuse, no fetch
                    segs = cache[vid]
                elif fetch_transcripts:                # fetch once, then cache
                    fetched = self.yt.fetch_segments(str(url))
                    if fetched:
                        segs = [[round(s, 1), t] for s, t in fetched]
                        cache[vid] = segs
            if segs:
                text = text + ". " + " ".join(t for _, t in segs)[:5000]
            cid += 1
            assets.append(Asset(
                id=cid, name=str(title).strip(), type=stype, source="public link",
                location=str(url or "").strip(), text=text, modified="",
            ))
            if segs:
                transcripts[str(cid)] = segs

        # 3) Embed every asset's text in one batch.
        embeddings = self.embedder.embed([a.text for a in assets])

        # 4) Save the index.
        idx = Path(index_dir)
        idx.mkdir(parents=True, exist_ok=True)
        np.save(idx / "embeddings.npy", np.asarray(embeddings, dtype="float32"))
        with open(idx / "catalog.json", "w", encoding="utf-8") as f:
            json.dump([a.__dict__ for a in assets], f, indent=2, ensure_ascii=False)
        with open(idx / "transcripts.json", "w", encoding="utf-8") as f:
            json.dump(transcripts, f, ensure_ascii=False)
        with open(cache_path, "w", encoding="utf-8") as f:   # persist the transcript cache
            json.dump(cache, f, ensure_ascii=False)
        return len(assets)
