import os, subprocess, sys

langs=[x.strip() for x in os.environ.get("ARGOS_SOURCE_LANGS","").split(",") if x.strip()]
if not langs:
    print("ARGOS_SOURCE_LANGS empty: English-only bridge until models are installed.")
    raise SystemExit(0)

script=os.path.join(os.path.dirname(__file__),"install_argos.py")
failed=[]
for lang in langs:
    if lang=="en":
        continue
    print(f"Installing Argos {lang} -> en")
    r=subprocess.run([sys.executable,script,lang,"en"])
    if r.returncode:
        failed.append(lang)

if failed:
    raise SystemExit("Failed Argos models: "+", ".join(failed))
