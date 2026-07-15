from pathlib import Path
import json, uuid
from datetime import datetime
from config import resource_root
from constants import *
from filesystem import ensure_dir
def slug(v): return v.lower().strip().replace(" ","-")
def city_path(root,country,province,city): return Path(root)/country/province/city
def list_pois(root,country,province,city):
 p=city_path(root,country,province,city)
 return sorted([x.name for x in p.iterdir() if x.is_dir()]) if p.exists() else []
def next_poi_number(pois):
 nums=[int(n.split("-",1)[0]) for n in pois if n.split("-",1)[0].isdigit()]
 return f"{max(nums,default=0)+1:02d}"
def read_template(name):
 p=resource_root()/"templates"/name
 return p.read_text(encoding="utf-8") if p.exists() else ""
def fill(c,d):
 for k,v in d.items(): c=c.replace("{{"+k+"}}",str(v))
 return c
def create_poi(root,country,province,city,number,name,category=""):
 name=name.strip(); poi=city_path(root,country,province,city)/f"{number}-{name}"
 if poi.exists(): raise FileExistsError(f"Ya existe el POI: {poi}")
 ensure_dir(poi/SHARED_IMAGES_FOLDER)
 pid=str(uuid.uuid5(uuid.NAMESPACE_DNS,f"{country}-{province}-{city}-{name}")); now=datetime.now().isoformat(timespec="seconds")
 data={"POI_ID":pid,"POI_NAME":name,"COUNTRY":country,"PROVINCE":province,"CITY":city,"CATEGORY":category,"UPDATED_AT":now}
 (poi/POI_MASTER_FILE).write_text(fill(read_template(POI_MASTER_TEMPLATE),data),encoding="utf-8")
 (poi/POI_JSON).write_text(json.dumps({"poi_id":pid,"poi_order":number,"poi_name":name,"category":category,"country":country,"province":province,"city":city,"country_slug":slug(country),"province_slug":slug(province),"city_slug":slug(city),"lat":"","lng":""},ensure_ascii=False,indent=4),encoding="utf-8")
 for lang in LANGUAGES:
  ld=poi/lang; ensure_dir(ld/AUDIO_FOLDER); x=data.copy(); x["LANG"]=LANG_CODES[lang]
  (ld/TEXT_FILE).write_text(fill(read_template(TEXT_TEMPLATE),x),encoding="utf-8")
  try:m=json.loads(fill(read_template(META_TEMPLATE),x))
  except Exception:m={}
  (ld/META_FILE).write_text(json.dumps(m,ensure_ascii=False,indent=4),encoding="utf-8")
 return poi
def find_master_file(poi):
 p=poi/POI_MASTER_FILE
 if p.exists(): return p
 old=sorted(poi.glob("POI_MASTER-*.md"))
 return old[0] if old else None
