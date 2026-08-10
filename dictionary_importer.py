from __future__ import annotations
import re, sqlite3
from pathlib import Path
from dictionary_db import DictionaryDB

VOL_CHARS = r"A-Za-zÄÖÜäöü"
VO_WORD = rf"[{VOL_CHARS}][{VOL_CHARS}'-]*"

def read_document(path: str):
    p=Path(path)
    ext=p.suffix.lower()
    if ext==".pdf":
        import fitz
        doc=fitz.open(p)
        for pi,page in enumerate(doc):
            for li,line in enumerate(page.get_text("text").splitlines()):
                yield pi+1,li+1,line.rstrip()
    elif ext==".docx":
        from docx import Document
        doc=Document(p)
        n=0
        for para in doc.paragraphs:
            for line in para.text.splitlines():
                n+=1
                yield None,n,line.rstrip()
    elif ext in {".txt",".text"}:
        for i,line in enumerate(p.read_text(encoding="utf-8",errors="replace").splitlines(),1):
            yield None,i,line.rstrip()
    else:
        raise ValueError("Supported: PDF, DOCX, TXT")

def normalize(line):
    return re.sub(r"\s+"," ",line.strip())

def guess_pos_en(head):
    h=head.strip()
    if h.lower().startswith("(to) "): return "VERB"
    if h.lower().startswith("to "): return "VERB"
    return None

def clean_head(head):
    h=re.sub(r"^\(to\)\s+","",head,flags=re.I)
    h=re.sub(r"^to\s+","",h,flags=re.I)
    return h.strip(" ;:,.").lower()

def parse_envo_line(line):
    x=normalize(line)
    if not x or x.startswith("- ") or re.fullmatch(r"\d+",x): return []
    if x.startswith(("*","•","**","***","****")): return []
    m=re.match(r"^(.+?)\s*=\s*(.+)$",x)
    sense=None
    if m:
        left,right=m.groups()
        sm=re.match(r"^(.*?)\s*\(([^()]*)\)\s*$",left)
        if sm: left,sense=sm.groups()
        pos=guess_pos_en(left)
        head=clean_head(left)
        vos=re.findall(rf"\b({VO_WORD}(?:ön|ik|o|io|i|e|a|s)?)\b",right)
        return [(head,v,pos,sense,0.86) for v in vos[:6] if len(v)>1]
    m=re.match(r"^\(to\)\s+(.+?)\s+("+VO_WORD+r"ön)(?:[;,\s]|$)",x,re.I)
    if m:
        return [(clean_head(m.group(1)),m.group(2),"VERB",None,0.93)]
    toks=x.split()
    if len(toks)>=2:
        v=toks[-1].strip(";,.")
        if re.fullmatch(VO_WORD,v) and (re.search(r"[äöüÄÖÜ]",v) or re.search(r"(ön|ik|an|am|od|ot|öp|em|av|ef|al|ül|äd|öf)$",v)):
            head=clean_head(" ".join(toks[:-1]))
            if head and re.search(r"[A-Za-z]",head):
                return [(head,v,guess_pos_en(" ".join(toks[:-1])),None,0.72)]
    return []

def parse_voen_line(line):
    x=normalize(line)
    if not x or x.startswith("- ") or x.startswith(("*","•")): return []
    m=re.match(rf"^({VO_WORD})\s+(.+)$",x)
    if not m:return []
    vo,rest=m.groups()
    rest=re.sub(r"\s*[;•*].*$","",rest).strip()
    if not rest:return []
    glosses=[g.strip().lower() for g in re.split(r"\s*[,/]\s*",rest) if g.strip()]
    out=[]
    for g in glosses[:5]:
        g=re.sub(r"^\(to\)\s+","",g)
        g=re.sub(r"\([^)]*\)","",g).strip(" .;:")
        if 0<len(g)<=80 and re.search(r"[a-z]",g):
            pos="VERB" if vo.endswith("ön") else ("ADJ" if vo.endswith("ik") else None)
            out.append((g,vo,pos,None,0.68))
    return out

def import_file(db: DictionaryDB, path: str, direction: str):
    parser=parse_envo_line if direction=="envo" else parse_voen_line
    with db.connect() as con:
        for page,line_no,text in read_document(path):
            if not text.strip(): continue
            cur=con.execute("INSERT INTO raw_lines(direction,page,line_no,text) VALUES(?,?,?,?)",
                            (direction,page,line_no,text))
            raw_id=cur.lastrowid
            for en,vo,pos,sense,conf in parser(text):
                con.execute("""INSERT INTO entries(english,volapuk,pos,sense,direction,source_line_id,parse_confidence)
                               VALUES(?,?,?,?,?,?,?)""",(en,vo,pos,sense,direction,raw_id,conf))

def rebuild_cross(db: DictionaryDB):
    with db.connect() as con:
        con.execute("DELETE FROM cross_entries")
        envo=con.execute("""SELECT lower(english),volapuk,pos,sense,max(parse_confidence)
                            FROM entries WHERE direction='envo'
                            GROUP BY lower(english),volapuk,pos,sense""").fetchall()
        voen=set((r[0],r[1]) for r in con.execute(
            "SELECT lower(english),volapuk FROM entries WHERE direction='voen'"
        ))
        for en,vo,pos,sense,conf in envo:
            cross=(en,vo) in voen
            grade="X2" if cross else "X1"
            final=min(0.99, conf + (0.10 if cross else 0))
            con.execute("""INSERT INTO cross_entries(english,volapuk,pos,sense,grade,confidence)
                           VALUES(?,?,?,?,?,?)""",(en,vo,pos,sense,grade,final))

def import_dictionaries(db_path, core_path, envo=None, voen=None, reset=False):
    db=DictionaryDB(db_path,core_path)
    with db.connect() as con:
        if reset:
            con.execute("DELETE FROM raw_lines");con.execute("DELETE FROM entries");con.execute("DELETE FROM cross_entries")
    if envo: import_file(db,envo,"envo")
    if voen: import_file(db,voen,"voen")
    rebuild_cross(db)
    return db.stats()
