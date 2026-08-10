import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dictionary_importer import import_dictionaries

p=argparse.ArgumentParser()
p.add_argument("--envo")
p.add_argument("--voen")
p.add_argument("--db",default=str(ROOT/"data/volapuk.sqlite3"))
p.add_argument("--reset",action="store_true")
a=p.parse_args()
stats=import_dictionaries(a.db,ROOT/"data/core_lexicon.json",a.envo,a.voen,a.reset)
print(stats)
