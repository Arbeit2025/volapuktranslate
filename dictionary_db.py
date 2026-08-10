from __future__ import annotations
import json, sqlite3, re
from pathlib import Path
from dataclasses import dataclass

from remote_dictionary import REMOTE_DICTIONARY

@dataclass
class LexicalCandidate:
    english: str
    volapuk: str
    pos: str | None
    sense: str | None
    grade: str
    source: str
    confidence: float


def english_lookup_forms(word: str) -> list[str]:
    """Conservative surface-form fallback for direct dictionary searches.

    spaCy already supplies lemmas to the translation engine. These rules mainly
    make the dictionary search box useful for ordinary inflected English input.
    """
    q = re.sub(r"\s+", " ", word.lower().strip())
    forms = [q]
    if " " not in q:
        if q.endswith("ies") and len(q) > 4:
            forms.append(q[:-3] + "y")
        if q.endswith("ied") and len(q) > 4:
            forms.append(q[:-3] + "y")
        if q.endswith("es") and len(q) > 4:
            forms.extend([q[:-2], q[:-1]])
        elif q.endswith("s") and len(q) > 3 and not q.endswith("ss"):
            forms.append(q[:-1])
        if q.endswith("ing") and len(q) > 5:
            stem = q[:-3]
            forms.extend([stem, stem + "e"])
            if len(stem) > 2 and stem[-1] == stem[-2]:
                forms.append(stem[:-1])
        if q.endswith("ed") and len(q) > 4:
            stem = q[:-2]
            forms.extend([stem, stem + "e"])
            if len(stem) > 2 and stem[-1] == stem[-2]:
                forms.append(stem[:-1])
    return list(dict.fromkeys(x for x in forms if x))


class DictionaryDB:
    def __init__(self, db_path: str | Path, core_path: str | Path):
        self.db_path = Path(db_path)
        self.core_path = Path(core_path)
        self.core = json.loads(self.core_path.read_text(encoding="utf-8"))["entries"]
        self.ensure_schema()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS raw_lines(
              id INTEGER PRIMARY KEY,
              direction TEXT NOT NULL,
              page INTEGER,
              line_no INTEGER,
              text TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS entries(
              id INTEGER PRIMARY KEY,
              english TEXT NOT NULL,
              volapuk TEXT NOT NULL,
              pos TEXT,
              sense TEXT,
              direction TEXT NOT NULL,
              source_line_id INTEGER,
              parse_confidence REAL NOT NULL DEFAULT 0.5
            );
            CREATE INDEX IF NOT EXISTS idx_entries_en ON entries(english);
            CREATE INDEX IF NOT EXISTS idx_entries_vo ON entries(volapuk);
            CREATE TABLE IF NOT EXISTS cross_entries(
              id INTEGER PRIMARY KEY,
              english TEXT NOT NULL,
              volapuk TEXT NOT NULL,
              pos TEXT,
              sense TEXT,
              grade TEXT NOT NULL,
              confidence REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cross_en ON cross_entries(english);
            """)

    def stats(self):
        with self.connect() as con:
            raw = con.execute("SELECT COUNT(*) FROM raw_lines").fetchone()[0]
            ent = con.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            x2 = con.execute("SELECT COUNT(*) FROM cross_entries WHERE grade='X2'").fetchone()[0]
            x1 = con.execute("SELECT COUNT(*) FROM cross_entries WHERE grade='X1'").fetchone()[0]
        return {
            "raw_lines": raw, "parsed_entries": ent, "x2": x2, "x1": x1,
            "core": len(self.core), "remote_cached": bool(REMOTE_DICTIONARY._index)
        }

    def lookup(self, english: str, pos: str | None = None) -> list[LexicalCandidate]:
        forms = english_lookup_forms(english)
        out: list[LexicalCandidate] = []

        for q in forms:
            for e in self.core:
                if e["en"].lower() == q and (not pos or e.get("pos") == pos):
                    out.append(LexicalCandidate(
                        english=e["en"], volapuk=e["vo"], pos=e.get("pos"),
                        sense=e.get("sense"), grade=e.get("grade","A"),
                        source="core", confidence=0.99
                    ))

        with self.connect() as con:
            for q in forms:
                if pos:
                    rows = con.execute("""
                        SELECT english,volapuk,pos,sense,grade,confidence
                        FROM cross_entries WHERE lower(english)=? AND (pos=? OR pos IS NULL)
                        ORDER BY confidence DESC
                    """,(q,pos)).fetchall()
                else:
                    rows = con.execute("""
                        SELECT english,volapuk,pos,sense,grade,confidence
                        FROM cross_entries WHERE lower(english)=?
                        ORDER BY confidence DESC
                    """,(q,)).fetchall()
                for r in rows:
                    out.append(LexicalCandidate(r[0],r[1],r[2],r[3],r[4],"imported",r[5]))

        # Runtime fallback to the official dictionary page. The dictionary text
        # itself is not redistributed in this repository.
        for q in forms:
            for r in REMOTE_DICTIONARY.lookup(q, pos):
                out.append(LexicalCandidate(
                    english=r.english, volapuk=r.volapuk, pos=r.pos,
                    sense=r.gloss, grade="R", source="official-remote", confidence=0.94
                ))

        dedup: list[LexicalCandidate] = []
        seen=set()
        for x in sorted(out, key=lambda c: c.confidence, reverse=True):
            key=(x.volapuk,x.pos,x.sense if x.source != "official-remote" else None)
            if key not in seen:
                dedup.append(x);seen.add(key)
        return dedup
