"""Motor de Investigación de UBIGUIA — orquestación agnóstica de entidad.

No conoce qué es un POI ni qué es Claude: solo conoce los contratos de
`entidad.py`, `estados.py`, `proveedor.py` y el adaptador de entidad que
se le pase. En la Etapa 1, el único adaptador disponible es el de POI.
"""
from datetime import datetime
from pathlib import Path

from motor_investigacion import estados
from motor_investigacion.entidades.poi import adaptador as adaptador_poi
from motor_investigacion.proveedor import ProveedorInvestigacion


def ejecutar_investigacion(poi_dir: Path, proveedor: ProveedorInvestigacion, actor: str = "agent") -> dict:
    """Ejecuta una investigación completa sobre un POI que todavía no
    tiene ninguna investigación asociada.

    Crea `_research/` con los cinco archivos y deja el estado en
    EN_REVISION. No aprueba ni promueve nada — eso es responsabilidad de
    una etapa posterior. Lanza ValueError si el POI ya tiene una
    investigación en curso (para eso corresponde retomarla, no volver a
    ejecutar_investigacion()).
    """
    carpeta_research = adaptador_poi.asegurar_carpeta_research(poi_dir)

    if estados.leer_estado(carpeta_research) is not None:
        raise ValueError(
            f"Ya existe una investigación para '{poi_dir.name}'; "
            "ejecutar_investigacion() solo aplica a investigaciones nuevas."
        )

    contexto = adaptador_poi.construir_contexto(poi_dir)

    estados.crear_estado_inicial(
        carpeta_research,
        entity_type=contexto.tipo_entidad,
        entity_id=contexto.id_entidad,
        provider=proveedor.nombre,
        model=proveedor.modelo,
    )
    adaptador_poi.inicializar_observaciones(poi_dir)

    resultado = proveedor.investigar_entidad(contexto)

    adaptador_poi.escribir_borrador(poi_dir, resultado)

    fuentes_json = [
        fuente.a_diccionario_json(f"src-{indice + 1:02d}") for indice, fuente in enumerate(resultado.fuentes)
    ]
    estados.actualizar_datos_investigacion(carpeta_research, fuentes_json, resultado.contradicciones_detectadas)

    return estados.cambiar_estado(carpeta_research, estados.EN_REVISION, actor=actor)


def promover_a_master(poi_dir: Path, actor: str = "editor") -> tuple[dict, str]:
    """Aprueba una investigación en EN_REVISION y promueve su borrador a
    POI_MASTER.md, de forma atómica y auditada.

    No permite aprobar si falta research.json, falta
    POI_MASTER_BORRADOR.md, o el estado actual no admite pasar a
    APROBADO. Si algo falla después de reemplazar POI_MASTER.md (por
    ejemplo, al actualizar research.json), se restaura el contenido
    anterior del archivo, se conserva el respaldo ya generado, y se
    registra un evento ERROR en el historial antes de volver a lanzar
    la excepción.

    Devuelve (research.json actualizado, nombre del archivo de respaldo).
    """
    carpeta_research = adaptador_poi.ruta_research(poi_dir)

    datos = estados.leer_estado(carpeta_research)
    if datos is None:
        raise ValueError(f"'{poi_dir.name}' no tiene una investigación (research.json no existe).")

    if not adaptador_poi.ruta_borrador_master(poi_dir).exists():
        raise ValueError(f"'{poi_dir.name}' no tiene POI_MASTER_BORRADOR.md.")

    estado_actual = datos["state"]
    if not estados.transicion_valida(estado_actual, estados.APROBADO):
        raise estados.TransicionInvalidaError(
            f"No se puede aprobar '{poi_dir.name}' desde el estado {estado_actual}; "
            f"se requiere {estados.EN_REVISION}."
        )

    ruta_master = adaptador_poi.ruta_master(poi_dir)
    contenido_master_previo = ruta_master.read_text(encoding="utf-8") if ruta_master.exists() else None

    nombre_backup = adaptador_poi.promover_borrador_a_master(poi_dir)

    try:
        ahora = datetime.now().isoformat(timespec="seconds")
        datos["state"] = estados.APROBADO
        datos["approved_at"] = ahora
        datos["updated_at"] = ahora
        estados.escribir_estado_atomico(carpeta_research, datos)
        estados.registrar_evento_historial(
            carpeta_research, {"timestamp": ahora, "event": "APPROVED", "actor": actor}
        )
        estados.registrar_evento_historial(
            carpeta_research,
            {"timestamp": ahora, "event": "PROMOTED", "actor": actor, "master_backup": nombre_backup},
        )
    except Exception as exc:
        if contenido_master_previo is not None:
            estados.escribir_archivo_atomico(ruta_master, contenido_master_previo)
        try:
            estados.registrar_evento_historial(
                carpeta_research,
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "event": "ERROR",
                    "actor": actor,
                    "detail": f"Falló la promoción a POI_MASTER.md: {exc}",
                },
            )
        except Exception:
            pass  # no ocultar la excepción original si ni el registro de error funciona
        raise

    return datos, nombre_backup
