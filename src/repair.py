from pathlib import Path
from constants import *
from filesystem import rewrite_utf8
from poi_manager import ensure_poi_structure
def title(p): return p.name.split("-",1)[1].strip() if "-" in p.name else p.name
def repair_poi(p):
 a=[]
 for broken,fixed in BROKEN_LANGUAGE_NAMES.items():
  old,new=p/broken,p/fixed
  if old.exists() and not new.exists(): old.rename(new); a.append(f"Renombrado {broken} -> {fixed}")
 master=p/POI_MASTER_FILE
 if not master.exists():
  old=sorted(p.glob("POI_MASTER-*.md"))
  if old: old[0].rename(master); a.append("MASTER antiguo renombrado")
  else: master.write_text(f"# POI MASTER\n\n# {title(p)}\n",encoding="utf-8"); a.append("Creado POI_MASTER.md")
 ensure_poi_structure(p)
 for lang in LANGUAGES:
  ld=p/lang
  if not (ld/TEXT_FILE).exists(): (ld/TEXT_FILE).write_text(f"# {title(p)}\n",encoding="utf-8"); a.append(f"Creado {lang}/texto.md")
  if not (ld/META_FILE).exists(): (ld/META_FILE).write_text("{}",encoding="utf-8"); a.append(f"Creado {lang}/meta.json")
 c=sum(1 for f in p.rglob("*") if f.is_file() and rewrite_utf8(f))
 if c:a.append(f"Archivos normalizados UTF-8: {c}")
 return a
def repair_city(city):
 r=[]
 if not city.exists(): return ["No existe la carpeta de ciudad."]
 for p in sorted([x for x in city.iterdir() if x.is_dir()]):
  a=repair_poi(p)
  if a:r.append(f"[{p.name}]"); r.extend([f" - {x}" for x in a])
 return r or ["No se encontraron cambios necesarios."]
