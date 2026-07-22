"""Adaptador de la entidad POI para el Motor de Investigación de UBIGUIA.

Único adaptador concreto implementado en v1.0. Es el único componente del
Motor de Investigación que sabe dónde y cómo vive un POI en el filesystem
de TURISMO. Reutiliza constants.py y filesystem.py ya existentes en el
proyecto.
"""
import json
from datetime import datetime
from pathlib import Path

from constants import POI_JSON, POI_MASTER_FILE
from filesystem import ensure_dir

from motor_investigacion.entidad import ContextoEntidad, ResultadoInvestigacion
from motor_investigacion.estados import escribir_archivo_atomico

NOMBRE_CARPETA_RESEARCH = "_research"
ARCHIVO_BORRADOR_MASTER = "POI_MASTER_BORRADOR.md"
ARCHIVO_FUENTES = "fuentes.md"
ARCHIVO_OBSERVACIONES = "observaciones.md"


def ruta_research(poi_dir: Path) -> Path:
    return poi_dir / NOMBRE_CARPETA_RESEARCH


def asegurar_carpeta_research(poi_dir: Path) -> Path:
    """Creación controlada de _research/: crea la carpeta si no existe,
    sin tocar nada más dentro del POI."""
    carpeta = ruta_research(poi_dir)
    ensure_dir(carpeta)
    return carpeta


def _leer_poi_json(poi_dir: Path) -> dict:
    ruta = poi_dir / POI_JSON
    if not ruta.exists():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


def construir_contexto(poi_dir: Path) -> ContextoEntidad:
    """Lee poi.json y POI_MASTER.md (sin modificarlos) para construir el
    contexto genérico que consume un proveedor de investigación."""
    datos_poi = _leer_poi_json(poi_dir)
    ruta_master = poi_dir / POI_MASTER_FILE
    ficha_actual = ruta_master.read_text(encoding="utf-8") if ruta_master.exists() else ""

    return ContextoEntidad(
        tipo_entidad="POI",
        id_entidad=datos_poi.get("poi_id", ""),
        nombre=datos_poi.get("poi_name", poi_dir.name),
        contexto_geografico={
            "ciudad": datos_poi.get("city", ""),
            "provincia": datos_poi.get("province", ""),
            "pais": datos_poi.get("country", ""),
            "categoria": datos_poi.get("category", ""),
        },
        ficha_actual=ficha_actual,
    )


def ruta_master(poi_dir: Path) -> Path:
    return poi_dir / POI_MASTER_FILE


def ruta_borrador_master(poi_dir: Path) -> Path:
    return ruta_research(poi_dir) / ARCHIVO_BORRADOR_MASTER


def ruta_fuentes(poi_dir: Path) -> Path:
    return ruta_research(poi_dir) / ARCHIVO_FUENTES


def ruta_observaciones(poi_dir: Path) -> Path:
    return ruta_research(poi_dir) / ARCHIVO_OBSERVACIONES


def _formatear_fuentes_md(resultado: ResultadoInvestigacion) -> str:
    if not resultado.fuentes:
        return "# Fuentes\n\n(Sin fuentes registradas.)\n"

    lineas = ["# Fuentes", ""]
    for fuente in resultado.fuentes:
        lineas.append(f"## {fuente.titulo}")
        lineas.append(f"- URL: {fuente.url}")
        lineas.append(f"- Sitio: {fuente.sitio}")
        lineas.append(f"- Consultado: {fuente.consultado_en}")
        lineas.append(f"- Confianza: {fuente.confianza}")
        if fuente.secciones_respaldadas:
            lineas.append(f"- Respalda: {', '.join(fuente.secciones_respaldadas)}")
        if fuente.notas:
            lineas.append(f"- Notas: {fuente.notas}")
        if fuente.contradicciones:
            lineas.append(f"- Contradicciones: {', '.join(fuente.contradicciones)}")
        lineas.append("")
    return "\n".join(lineas) + "\n"


def escribir_borrador(poi_dir: Path, resultado: ResultadoInvestigacion) -> None:
    """Escribe POI_MASTER_BORRADOR.md y fuentes.md de forma atómica.
    Nunca toca POI_MASTER.md."""
    asegurar_carpeta_research(poi_dir)
    escribir_archivo_atomico(ruta_borrador_master(poi_dir), resultado.borrador_master)
    escribir_archivo_atomico(ruta_fuentes(poi_dir), _formatear_fuentes_md(resultado))


def inicializar_observaciones(poi_dir: Path) -> None:
    """Crea observaciones.md vacío si todavía no existe, sin sobrescribir
    observaciones ya escritas por el editor."""
    ruta = ruta_observaciones(poi_dir)
    if not ruta.exists():
        escribir_archivo_atomico(ruta, "# Observaciones\n\n(Sin observaciones todavía.)\n")


def nombre_backup_master() -> str:
    marca_tiempo = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{POI_MASTER_FILE}.bak-{marca_tiempo}"


def promover_borrador_a_master(poi_dir: Path) -> str:
    """Respalda POI_MASTER.md (si existe) y lo reemplaza de forma
    atómica por el contenido de POI_MASTER_BORRADOR.md. Nunca dejar
    POI_MASTER.md vacío o a medio escribir: el respaldo se guarda antes
    de tocar el archivo original, y el reemplazo usa el mismo escritor
    atómico que el resto del Motor de Investigación.

    Devuelve el nombre del archivo de respaldo generado."""
    ruta_actual = ruta_master(poi_dir)
    contenido_borrador = ruta_borrador_master(poi_dir).read_text(encoding="utf-8")

    nombre_backup = nombre_backup_master()
    if ruta_actual.exists():
        ruta_backup = ruta_actual.parent / nombre_backup
        escribir_archivo_atomico(ruta_backup, ruta_actual.read_text(encoding="utf-8"))

    escribir_archivo_atomico(ruta_actual, contenido_borrador)
    return nombre_backup
