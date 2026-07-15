from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from datetime import datetime
import json
def safe(v): return v.strip().replace(" ","_").replace("/","_").replace("\\","_")
def next_file(root,city):
 root.mkdir(parents=True,exist_ok=True); today=datetime.now().strftime("%Y%m%d"); pref=f"{safe(city)}_POIS_{today}_v"; ex=sorted(root.glob(f"{pref}*.zip")); return root/f"{pref}{len(ex)+1:03d}.zip"
def export_pois(export_root,turismo_root,country,province,city,pois):
 zpath=next_file(export_root,city); manifest={"manifest_version":"1.0","created_at":datetime.now().isoformat(timespec="seconds"),"country":country,"province":province,"city":city,"count":len(pois),"pois":[p.name for p in pois]}
 with ZipFile(zpath,"w",ZIP_DEFLATED) as z:
  z.writestr("MANIFIESTO.json",json.dumps(manifest,ensure_ascii=False,indent=4))
  for poi in pois:
   for f in poi.rglob("*"):
    if f.is_file(): z.write(f,Path(country)/province/city/poi.name/f.relative_to(poi))
 return zpath
