"""Contratos de datos genéricos del Motor de Investigación de UBIGUIA.

Estos contratos no conocen ningún tipo de entidad concreto (ni POI ni
ningún otro): son el punto de acuerdo entre el Motor, los adaptadores de
entidad y los proveedores de investigación.
"""
from dataclasses import dataclass, field

# Valores permitidos para ResultadoInvestigacion.nivel_confianza, tal como
# los define el Prompt Maestro de Investigación (sección 3.7 y sección 13,
# "Control de calidad").
NIVELES_CONFIANZA_VALIDOS = ("ALTO", "MEDIO", "BAJO")


@dataclass
class ContextoEntidad:
    """Información que un adaptador de entidad construye para que un
    proveedor de investigación pueda investigarla."""

    tipo_entidad: str
    id_entidad: str
    nombre: str
    contexto_geografico: dict
    ficha_actual: str


@dataclass
class FuenteInvestigacion:
    titulo: str
    url: str
    sitio: str
    consultado_en: str
    secciones_respaldadas: list[str] = field(default_factory=list)
    confianza: str = ""
    notas: str = ""
    contradicciones: list[str] = field(default_factory=list)
    identificador: str = ""

    def a_diccionario_json(self, id_fuente: str) -> dict:
        """Convierte al esquema de research.json.sources ya aprobado
        (los nombres de campo del JSON quedan tal como fueron cerrados
        en la especificación; no se traducen)."""
        return {
            "id": id_fuente,
            "title": self.titulo,
            "url": self.url,
            "site": self.sitio,
            "consulted_at": self.consultado_en,
            "supports_sections": list(self.secciones_respaldadas),
            "confidence": self.confianza,
            "notes": self.notas,
            "contradictions": list(self.contradicciones),
        }


@dataclass
class MetadatosProveedor:
    """Identifica qué proveedor y qué modelo produjeron un resultado de
    investigación. Viaja dentro del propio resultado para que quede
    trazable de forma autocontenida, independientemente de cómo el Motor
    haya invocado al proveedor."""

    nombre: str
    modelo: str


@dataclass
class ResultadoInvestigacion:
    borrador_master: str
    fuentes: list[FuenteInvestigacion] = field(default_factory=list)
    contradicciones_detectadas: list[dict] = field(default_factory=list)
    observaciones: str = ""
    nivel_confianza: str = ""
    metadatos_proveedor: MetadatosProveedor | None = None


@dataclass
class CandidatoPOI:
    """Candidato propuesto por descubrir_entidades(). No se usa en la
    Etapa 1 (el descubrimiento no está implementado todavía)."""

    nombre: str
    categoria: str
    descripcion_breve: str
    relevancia_estimada: str
    fuentes: list[FuenteInvestigacion] = field(default_factory=list)
    justificacion: str = ""
