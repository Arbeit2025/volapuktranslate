from flask import Flask, render_template, request, jsonify
from dataclasses import asdict
from pathlib import Path
import os
from dictionary_db import DictionaryDB
from dictionary_importer import import_dictionaries
from bridge import to_english
from english_engine import EnglishToVolapuk

BASE=Path(__file__).resolve().parent
DB_PATH=Path(os.environ.get("VOLAPUK_DB_PATH", str(BASE/"data/volapuk.sqlite3")))
UPLOAD_DIR=Path(os.environ.get("VOLAPUK_UPLOAD_DIR", str(DB_PATH.parent/"uploads")))
DB=DictionaryDB(DB_PATH,BASE/"data/core_lexicon.json")
ENGINE=EnglishToVolapuk(DB)

app=Flask(__name__,max_content_length=32*1024*1024)

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/healthz")
def healthz():
    return {"ok": True, "db": DB.stats()}

@app.get("/api/stats")
def stats():
    return jsonify(DB.stats())

@app.post("/api/translate")
def translate_api():
    j=request.get_json(force=True)
    text=(j.get("text") or "").strip()
    source=j.get("source_lang","auto")
    if not text:return jsonify({"status":"HOLD","error":"empty text"}),400
    bridge=to_english(text,source)
    if bridge.status=="HOLD":
        return jsonify({"status":"HOLD","bridge":asdict(bridge),"sentences":[]})
    global_status,results=ENGINE.translate_text(bridge.english)
    if bridge.status=="REVIEW":
        global_status="REVIEW" if global_status=="READY" else global_status
    return jsonify({
        "status":global_status,
        "bridge":asdict(bridge),
        "sentences":[asdict(r) for r in results],
        "output":"\n".join(r.output for r in results if r.output)
    })

@app.post("/api/import")
def import_api():
    envo=request.files.get("envo")
    voen=request.files.get("voen")
    if not envo and not voen:return jsonify({"error":"choose at least one dictionary file"}),400
    up=UPLOAD_DIR;up.mkdir(parents=True,exist_ok=True)
    ep=vp=None
    if envo:
        ep=up/envo.filename;envo.save(ep)
    if voen:
        vp=up/voen.filename;voen.save(vp)
    st=import_dictionaries(DB_PATH,BASE/"data/core_lexicon.json",
                           str(ep) if ep else None,str(vp) if vp else None,reset=True)
    return jsonify(st)

@app.get("/api/search")
def search():
    q=(request.args.get("q") or "").strip()
    pos=request.args.get("pos") or None
    return jsonify([asdict(x) for x in DB.lookup(q,pos)])

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")),debug=False)
