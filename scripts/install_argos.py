import argparse
import argostranslate.package

p=argparse.ArgumentParser()
p.add_argument("src",nargs="?")
p.add_argument("dst",nargs="?",default="en")
p.add_argument("--list",action="store_true")
a=p.parse_args()

argostranslate.package.update_package_index()
pkgs=argostranslate.package.get_available_packages()

if a.list:
    for x in pkgs:
        print(f"{x.from_code:6} -> {x.to_code:6} {x.package_version}")
    raise SystemExit

if not a.src:
    raise SystemExit("Specify source language code, e.g. ja en")

matches=[x for x in pkgs if x.from_code==a.src and x.to_code==a.dst]
if not matches:
    raise SystemExit(f"No package found: {a.src} -> {a.dst}")
pkg=matches[0]
print("Downloading",pkg)
argostranslate.package.install_from_path(pkg.download())
print("Installed",a.src,"->",a.dst)
