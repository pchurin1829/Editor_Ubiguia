from pathlib import Path
import json, shutil, sys
from constants import CONFIG_LOCAL_FILE, CONFIG_TEMPLATE_FILE
DEFAULT_CONFIG={"version":"1.0","turismo_root":"","last_country":"ARGENTINA","last_province":"BUENOS AIRES","last_city":"LA PLATA","window_width":1180,"window_height":760}
def app_root(): return Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent.parent
def resource_root(): return Path(sys._MEIPASS) if getattr(sys,"frozen",False) and hasattr(sys,"_MEIPASS") else app_root()
def project_root(): return app_root()
def config_path(): return app_root()/CONFIG_LOCAL_FILE
def ensure_local_config():
 p=config_path()
 if p.exists(): return
 t=app_root()/CONFIG_TEMPLATE_FILE
 shutil.copyfile(t,p) if t.exists() else p.write_text(json.dumps(DEFAULT_CONFIG,ensure_ascii=False,indent=4),encoding="utf-8")
def load_config():
 ensure_local_config()
 try:d=json.loads(config_path().read_text(encoding="utf-8"))
 except Exception:d=DEFAULT_CONFIG.copy()
 for k,v in DEFAULT_CONFIG.items(): d.setdefault(k,v)
 return d
def save_config(d): config_path().write_text(json.dumps(d,ensure_ascii=False,indent=4),encoding="utf-8")
