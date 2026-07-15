from pathlib import Path
import os
import subprocess
import sys

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def list_dirs(path: Path) -> list[str]:
    if not path or not path.exists() or not path.is_dir():
        return []
    return sorted([p.name for p in path.iterdir() if p.is_dir()])

def open_folder(path: Path) -> None:
    if not path.exists():
        return
    if sys.platform.startswith("win"):
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])

def open_file(path: Path) -> None:
    if not path.exists():
        return
    if sys.platform.startswith("win"):
        if path.suffix.lower() in [".md", ".txt", ".json"]:
            subprocess.Popen(["notepad.exe", str(path)])
        else:
            os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])

def safe_read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            pass
    return ""

def rewrite_utf8(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if path.suffix.lower() not in [".md", ".json", ".txt"]:
        return False
    content = safe_read_text(path)
    try:
        path.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False
