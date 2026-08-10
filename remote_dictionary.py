from __future__ import annotations

import re
import time
from dataclasses import dataclass
from html import unescape

import requests

VEDIC_URL = "https://xn--volapk-7ya.com/bowks.net/worldlang/volapuk/VEdic.htm"
USER_AGENT = "VolapukTranslate/1.1 (+https://github.com/Arbeit2025/volapuktranslate)"

VO_HEAD = re.compile(r"^[A-ZÄÖÜ][A-ZÄÖÜ'-]*(?:\s*\([^)]*\))?$")
ENTRY_SPLIT = re.compile(
    r"(?:^|\s)([A-ZÄÖÜ][A-ZÄÖÜ'\-]*(?:\s*\([^)]*\))?)\s*=\s*(.*?)"
    r"(?=(?:\s+[A-ZÄÖÜ][A-ZÄÖÜ'\-]*(?:\s*\([^)]*\))?\s*=)|$)"
)


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return unescape(html).replace("\xa0", " ")


def _normalise_english_gloss(s: str) -> str:
    s = s.lower().strip(" .;:,!?\t")
    s = re.sub(r"^\(to\)\s+", "", s)
    s = re.sub(r"^to\s+", "", s)
    s = re.sub(r"^(?:a|an|the)\s+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _guess_pos(vo: str, gloss: str) -> str | None:
    head = vo.split()[0]
    if head.endswith("ÖN"):
        return "VERB"
    if head.endswith("IK"):
        return "ADJ"
    if head.endswith("O") and not head.endswith("ÖN"):
        return "ADV"
    if re.match(r"^(?:to|\(to\))\s+", gloss.strip(), re.I):
        return "VERB"
    return "NOUN"


def _simple_variants(gloss: str) -> set[str]:
    """Return conservative search keys for an English dictionary gloss.

    We intentionally do not try to understand arbitrary definitions here. Only
    short synonym-like pieces are indexed for automatic lookup.
    """
    raw = gloss.strip()
    pieces = re.split(r"\s*[;,/]\s*", raw)
    out: set[str] = set()
    for p in pieces[:8]:
        p = re.sub(r"\([^)]*\)", "", p).strip()
        n = _normalise_english_gloss(p)
        if n and len(n) <= 60 and not any(ch in n for ch in "=*[]"):
            out.add(n)
    return out


@dataclass(frozen=True)
class RemoteEntry:
    english: str
    volapuk: str
    pos: str | None
    gloss: str


class RemoteVolapukDictionary:
    """Read-through cache for the public Volapük-English dictionary webpage.

    The dictionary content is not committed to this repository. It is fetched
    from the source site at runtime, parsed into an in-memory reverse index and
    refreshed periodically.
    """

    def __init__(self, ttl_seconds: int = 24 * 60 * 60):
        self.ttl_seconds = ttl_seconds
        self._loaded_at = 0.0
        self._index: dict[str, list[RemoteEntry]] = {}
        self._error: str | None = None

    @property
    def error(self) -> str | None:
        return self._error

    def _fresh(self) -> bool:
        return bool(self._index) and (time.time() - self._loaded_at) < self.ttl_seconds

    def refresh(self) -> None:
        response = requests.get(
            VEDIC_URL,
            timeout=25,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        )
        response.raise_for_status()
        text = _strip_html(response.text)
        index: dict[str, list[RemoteEntry]] = {}

        for raw_line in text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if "=" not in line or line.startswith("---"):
                continue
            for m in ENTRY_SPLIT.finditer(line):
                vo_raw, gloss = m.groups()
                vo = re.sub(r"\s*\([^)]*\)\s*$", "", vo_raw).strip()
                if not vo or not gloss:
                    continue
                pos = _guess_pos(vo, gloss)
                for key in _simple_variants(gloss):
                    entry = RemoteEntry(key, vo.lower(), pos, gloss.strip())
                    bucket = index.setdefault(key, [])
                    if not any(x.volapuk == entry.volapuk and x.pos == entry.pos for x in bucket):
                        bucket.append(entry)

        if not index:
            raise RuntimeError("remote dictionary parsed zero entries")
        self._index = index
        self._loaded_at = time.time()
        self._error = None

    def lookup(self, english: str, pos: str | None = None) -> list[RemoteEntry]:
        if not self._fresh():
            try:
                self.refresh()
            except Exception as exc:
                self._error = str(exc)
                if not self._index:
                    return []
        q = _normalise_english_gloss(english)
        rows = self._index.get(q, [])
        if pos:
            rows = [x for x in rows if x.pos == pos or x.pos is None]
        return rows


REMOTE_DICTIONARY = RemoteVolapukDictionary()
