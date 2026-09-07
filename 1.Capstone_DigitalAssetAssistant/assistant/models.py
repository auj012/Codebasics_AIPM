"""Plain data objects passed around the system."""
from dataclasses import dataclass


@dataclass
class Asset:
    """One item in the library: a file or a published link, plus its searchable text."""
    id: int
    name: str
    type: str          # deck | pdf | image | youtube | linkedin | website
    source: str        # "local file" | "public link"
    location: str      # file path (for files) or URL (for links)
    text: str          # the text we search over (filename + content inside)
    modified: str = "" # YYYY-MM-DD (used for recency ranking; blank for links)
    slide_page: str = ""  # where the match is, when known (future use)


@dataclass
class SearchResult:
    """One search hit: the asset, how well it matched, and a preview snippet."""
    asset: Asset
    score: float
    matched_snippet: str = ""
