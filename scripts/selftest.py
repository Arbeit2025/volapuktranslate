import tempfile, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dictionary_db import DictionaryDB
from dictionary_importer import import_dictionaries

def main():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        core=td/"core.json"
        core.write_text(json.dumps({"entries":[]}),encoding="utf-8")
        en=td/"en.txt"; vo=td/"vo.txt"
        en.write_text("(to) test testön\nsample sam\n",encoding="utf-8")
        vo.write_text("testön test\nsam sample\n",encoding="utf-8")
        dbp=td/"d.sqlite3"
        st=import_dictionaries(dbp,core,en,vo,reset=True)
        db=DictionaryDB(dbp,core)
        assert db.lookup("test")
        print("OK",st)
if __name__=="__main__":main()
