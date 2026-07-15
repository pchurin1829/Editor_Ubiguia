from pathlib import Path
import shutil
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT
PAYLOAD = ROOT / "payload" / "src"
TARGET = PROJECT / "src"

FILES = ["chatgpt_workflow.py", "ui_chatgpt.py", "main.py"]


def fail(message: str) -> None:
    print(f"\nERROR: {message}\n")
    input("Presione ENTER para cerrar...")
    sys.exit(1)


if not (TARGET / "ui_main.py").exists():
    fail("No se encontró el proyecto completo en src. Falta ui_main.py.")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = PROJECT / "backup_patch_chatgpt" / stamp
backup.mkdir(parents=True, exist_ok=True)

for name in FILES:
    source = PAYLOAD / name
    destination = TARGET / name

    if not source.exists():
        fail(f"Falta el archivo del parche: {source}")

    if destination.exists():
        shutil.copy2(destination, backup / name)

    shutil.copy2(source, destination)

print("\nPATCH CHATGPT CORREGIDO APLICADO\n")
print("Archivos instalados:")
for name in FILES:
    print(f"  src\\{name}")
print(f"\nCopia de seguridad: {backup}")
print("\nAhora pruebe: python src\\main.py")
input("\nPresione ENTER para cerrar...")
