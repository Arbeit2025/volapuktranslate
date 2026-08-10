from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass
class BridgeResult:
    source_lang: str
    english: str
    path: list[str]
    status: str
    note: str = ""

def detect_language(text):
    if re.fullmatch(r"[\x00-\x7F\s\W]+",text or ""):
        try:
            from langdetect import detect
            d=detect(text)
            return d if d else "en"
        except Exception:
            return "en"
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return "unknown"

def _installed_argos_languages():
    import argostranslate.translate
    return argostranslate.translate.get_installed_languages()

def _find_route(src,dst="en"):
    langs=_installed_argos_languages()
    by={x.code:x for x in langs}
    if src not in by or dst not in by:return None
    direct=by[src].get_translation(by[dst])
    if direct:return [src,dst]
    for mid in by:
        if mid in {src,dst}:continue
        if by[src].get_translation(by[mid]) and by[mid].get_translation(by[dst]):
            return [src,mid,dst]
    return None

def to_english(text,source_lang="auto"):
    lang=detect_language(text) if source_lang=="auto" else source_lang
    if lang=="en":
        return BridgeResult("en",text,["en"],"READY")
    try:
        import argostranslate.translate
        route=_find_route(lang,"en")
        if not route:
            return BridgeResult(lang,"",[],"HOLD",
                f"No installed Argos route from {lang} to en. Install a model first.")
        cur=text
        langs={x.code:x for x in _installed_argos_languages()}
        for a,b in zip(route,route[1:]):
            cur=langs[a].get_translation(langs[b]).translate(cur)
        status="READY" if len(route)==2 else "REVIEW"
        note="" if status=="READY" else "Argos pivot route used: "+" -> ".join(route)
        return BridgeResult(lang,cur,route,status,note)
    except Exception as e:
        return BridgeResult(lang,"",[],"HOLD","Argos unavailable: "+str(e))
