"""Estados del Motor de Investigación de UBIGUIA.

Define los estados válidos, las transiciones permitidas entre ellos, y la
persistencia atómica de research.json y el registro append-only de
historial.json. No conoce ningún tipo de entidad (ni POI ni ningún otro).
"""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

BORRADOR = "BORRADOR"
EN_REVISION = "EN_REVISION"
OBSERVADO = "OBSERVADO"
APROBADO = "APROBADO"
EXPORTADO = "EXPORTADO"

ESTADOS_VALIDOS = {BORRADOR, EN_REVISION, OBSERVADO, APROBADO, EXPORTADO}

# None representa "todavía no existe research.json" — la única transición
# válida desde ahí es la creación inicial en BORRADOR.
TRANSICIONES_VALIDAS = {
    None: {BORRADOR},
    BORRADOR: {EN_REVISION},
    EN_REVISION: {OBSERVADO, APROBADO},
    OBSERVADO: {EN_REVISION},
    APROBADO: {EN_REVISION, EXPORTADO},
    EXPORTADO: set(),
}

NOMBRE_ARCHIVO_ESTADO = "research.json"
NOMBRE_ARCHIVO_HISTORIAL = "historial.json"


class TransicionInvalidaError(Exception):
    """Se intentó una transición de estado no permitida."""


def transicion_valida(estado_actual: str | None, estado_nuevo: str) -> bool:
    return estado_nuevo in TRANSICIONES_VALIDAS.get(estado_actual, set())


def escribir_archivo_atomico(ruta: Path, contenido: str) -> None:
    """Escribe contenido a un archivo temporal y lo promueve al nombre
    final solo si la escritura fue completa, para no dejar nunca un
    archivo a medio escribir en `ruta`."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=ruta.parent, prefix=f".{ruta.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as archivo_temporal:
            archivo_temporal.write(contenido)
        os.replace(temp_path, ruta)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def _ruta_estado(carpeta_research: Path) -> Path:
    return carpeta_research / NOMBRE_ARCHIVO_ESTADO


def _ruta_historial(carpeta_research: Path) -> Path:
    return carpeta_research / NOMBRE_ARCHIVO_HISTORIAL


def leer_estado(carpeta_research: Path) -> dict | None:
    ruta = _ruta_estado(carpeta_research)
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_estado_atomico(carpeta_research: Path, datos: dict) -> None:
    escribir_archivo_atomico(_ruta_estado(carpeta_research), json.dumps(datos, ensure_ascii=False, indent=2))


def leer_historial(carpeta_research: Path) -> list:
    ruta = _ruta_historial(carpeta_research)
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def registrar_evento_historial(carpeta_research: Path, evento: dict) -> None:
    """Agrega un evento al final de historial.json sin tocar los
    eventos ya registrados (append-only)."""
    eventos = leer_historial(carpeta_research)
    eventos.append(evento)
    escribir_archivo_atomico(_ruta_historial(carpeta_research), json.dumps(eventos, ensure_ascii=False, indent=2))


def crear_estado_inicial(carpeta_research: Path, entity_type: str, entity_id: str, provider: str, model: str) -> dict:
    """Crea research.json en estado BORRADOR. Falla si ya existe uno."""
    if leer_estado(carpeta_research) is not None:
        raise ValueError(f"Ya existe {NOMBRE_ARCHIVO_ESTADO} en {carpeta_research}; no se puede crear de nuevo.")
    ahora = datetime.now().isoformat(timespec="seconds")
    datos = {
        "schema_version": "1.0",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "state": BORRADOR,
        "provider": provider,
        "model": model,
        "created_at": ahora,
        "updated_at": ahora,
        "approved_at": None,
        "exported_at": None,
        "export_zip": None,
        "sources": [],
        "contradictions_detected": [],
    }
    escribir_estado_atomico(carpeta_research, datos)
    registrar_evento_historial(carpeta_research, {"timestamp": ahora, "event": "CREATED", "actor": "agent"})
    return datos


def actualizar_datos_investigacion(carpeta_research: Path, fuentes: list[dict], contradicciones: list[dict]) -> dict:
    """Actualiza fuentes y contradicciones sin tocar el estado ni el historial."""
    datos = leer_estado(carpeta_research)
    if datos is None:
        raise ValueError(f"No existe {NOMBRE_ARCHIVO_ESTADO} en {carpeta_research}.")
    datos["sources"] = fuentes
    datos["contradictions_detected"] = contradicciones
    datos["updated_at"] = datetime.now().isoformat(timespec="seconds")
    escribir_estado_atomico(carpeta_research, datos)
    return datos


def cambiar_estado(carpeta_research: Path, estado_nuevo: str, actor: str, detalle: str | None = None) -> dict:
    """Valida y aplica una transición de estado, registrándola en el
    historial. Lanza TransicionInvalidaError si la transición no está
    permitida."""
    datos = leer_estado(carpeta_research)
    if datos is None:
        raise ValueError(f"No existe {NOMBRE_ARCHIVO_ESTADO} en {carpeta_research}.")
    estado_actual = datos["state"]
    if not transicion_valida(estado_actual, estado_nuevo):
        raise TransicionInvalidaError(f"Transición inválida: {estado_actual} -> {estado_nuevo}")
    ahora = datetime.now().isoformat(timespec="seconds")
    datos["state"] = estado_nuevo
    datos["updated_at"] = ahora
    escribir_estado_atomico(carpeta_research, datos)
    evento = {"timestamp": ahora, "event": "STATE_CHANGE", "from": estado_actual, "to": estado_nuevo, "actor": actor}
    if detalle:
        evento["detail"] = detalle
    registrar_evento_historial(carpeta_research, evento)
    return datos
