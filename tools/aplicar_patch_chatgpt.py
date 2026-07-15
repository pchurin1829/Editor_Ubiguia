
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
MAIN = SRC / "main.py"
BACKUP = SRC / "main.py.antes_chatgpt"

IMPORT_LINE = "from ui_chatgpt import apply_chatgpt_workflow"
APPLY_LINE = "apply_chatgpt_workflow(EditorUBIGUIA)"


def fail(message: str) -> None:
    print()
    print("ERROR:", message)
    print()
    input("Presione ENTER para cerrar...")
    sys.exit(1)


if not MAIN.exists():
    fail("No se encontró src\\main.py.")

if not (SRC / "ui_main.py").exists():
    fail(
        "La carpeta src no parece ser la del proyecto completo. "
        "Falta ui_main.py."
    )

content = MAIN.read_text(encoding="utf-8")

if not BACKUP.exists():
    shutil.copy2(MAIN, BACKUP)

if IMPORT_LINE not in content:
    lines = content.splitlines()

    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            insert_at = index + 1

    lines.insert(insert_at, IMPORT_LINE)
    content = "\n".join(lines) + "\n"

if APPLY_LINE not in content:
    marker = "def main():"

    if marker not in content:
        fail(
            "No se encontró 'def main():' en src\\main.py. "
            "No se realizó ningún cambio."
        )

    content = content.replace(
        marker,
        APPLY_LINE + "\n\n" + marker,
        1,
    )

MAIN.write_text(
    content,
    encoding="utf-8",
    newline="\n",
)

print()
print("PATCH APLICADO CORRECTAMENTE")
print()
print("Archivos agregados:")
print("  src\\chatgpt_workflow.py")
print("  src\\ui_chatgpt.py")
print()
print("Archivo modificado:")
print("  src\\main.py")
print()
print("Copia de seguridad:")
print("  src\\main.py.antes_chatgpt")
print()
input("Presione ENTER para cerrar...")
