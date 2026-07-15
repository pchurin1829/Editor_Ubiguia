from pathlib import Path
import os, subprocess, sys
def ensure_dir(p): p.mkdir(parents=True,exist_ok=True)
def list_dirs(p): return sorted([x.name for x in p.iterdir() if x.is_dir()]) if p and p.exists() and p.is_dir() else []
def open_folder(p):
 if not p.exists(): return
 os.startfile(str(p)) if sys.platform.startswith("win") else subprocess.Popen(["open" if sys.platform=="darwin" else "xdg-open",str(p)])
def safe_read_text(p):
 for e in ("utf-8","utf-8-sig","cp1252","latin-1"):
  try:return p.read_text(encoding=e)
  except Exception: pass
 return ""
def rewrite_utf8(p):
 if not p.exists() or not p.is_file() or p.suffix.lower() not in [".md",".json",".txt"]: return False
 try:p.write_text(safe_read_text(p),encoding="utf-8"); return True
 except Exception:return False
