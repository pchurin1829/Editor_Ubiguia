"""Contratos de datos genéricos del Motor de Investigación de UBIGUIA.

Estos contratos no conocen ningún tipo de entidad concreto (ni POI ni
ningún otro): son el punto de acuerdo entre el Motor, los adaptadores de
entidad y los proveedores de investigación.

Telemetría: los contratos de esta sección (UsoTokens, UsoBusquedaWeb,
TarifaModelo, CostosInvestigacion, MetricasInvestigacion) son genéricos
a propósito — no conocen nada específico de Anthropic ni de ningún otro
proveedor concreto. Cada proveedor decide cómo llenarlos (o si los deja
en None); el Motor y el adaptador de entidad solo saben persistirlos.
"""
from dataclasses import dataclass, field
from decimal import Decimal

# Valores permitidos para ResultadoInvestigacion.nivel_confianza, tal como
# los define el Prompt Maestro de Investigación (sección 3.7 y sección 13,
# "Control de calidad").
NIVELES_CONFIANZA_VALIDOS = ("ALTO", "MEDIO", "BAJO")

# Valores permitidos para MetricasInvestigacion.resultado.
RESULTADO_OK = "OK"
RESULTADO_ERROR = "ERROR"


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
class UsoTokens:
    """Tokens reportados por el proveedor para un intento de
    investigación. Cada campo es None cuando el dato no está disponible
    (nunca se completa con una estimación inventada)."""

    entrada: int | None = None
    salida: int | None = None
    cache_escritura: int | None = None
    cache_lectura: int | None = None

    def total_facturable_estimado(self) -> int | None:
        valores = (self.entrada, self.salida, self.cache_escritura, self.cache_lectura)
        if any(valor is None for valor in valores):
            return None
        return sum(valores)

    def a_diccionario_json(self) -> dict:
        return {
            "entrada": self.entrada,
            "salida": self.salida,
            "cache_escritura": self.cache_escritura,
            "cache_lectura": self.cache_lectura,
            "total_facturable_estimado": self.total_facturable_estimado(),
        }


@dataclass
class UsoBusquedaWeb:
    """Uso de la herramienta de búsqueda web reportado por el proveedor.
    `busquedas_exitosas` y `busquedas_con_error` distinguen explícitamente
    las búsquedas que sí se pueden facturar de las que fallaron (una
    búsqueda con error no se considera facturable)."""

    solicitudes_reportadas: int | None = None
    busquedas_exitosas: int | None = None
    busquedas_con_error: int | None = None
    codigos_error: list[str] = field(default_factory=list)

    def a_diccionario_json(self) -> dict:
        return {
            "solicitudes_reportadas": self.solicitudes_reportadas,
            "busquedas_exitosas": self.busquedas_exitosas,
            "busquedas_con_error": self.busquedas_con_error,
            "codigos_error": list(self.codigos_error),
        }


@dataclass
class TarifaModelo:
    """Tarifa oficial usada para calcular el costo de un intento
    concreto. Se guarda junto con la métrica para que quede trazable con
    qué tarifa se calculó, incluso si la tarifa cambia más adelante."""

    moneda: str
    modelo: str
    vigente_desde: str
    fuente: str

    def a_diccionario_json(self) -> dict:
        return {
            "moneda": self.moneda,
            "modelo": self.modelo,
            "vigente_desde": self.vigente_desde,
            "fuente": self.fuente,
        }


@dataclass
class CostosInvestigacion:
    """Costo estimado en USD de un intento, calculado únicamente a
    partir de métricas reportadas por la API (nunca inventado). Usa
    Decimal para evitar errores de precisión de punto flotante en
    valores monetarios. `costo_completo` es False cuando falta algún
    componente y el total no puede considerarse definitivo."""

    tokens_entrada: Decimal | None = None
    tokens_salida: Decimal | None = None
    cache_escritura: Decimal | None = None
    cache_lectura: Decimal | None = None
    busqueda_web: Decimal | None = None
    total_estimado: Decimal | None = None
    costo_completo: bool = False

    def a_diccionario_json(self) -> dict:
        def _texto(valor: Decimal | None) -> str | None:
            return str(valor) if valor is not None else None

        return {
            "tokens_entrada": _texto(self.tokens_entrada),
            "tokens_salida": _texto(self.tokens_salida),
            "cache_escritura": _texto(self.cache_escritura),
            "cache_lectura": _texto(self.cache_lectura),
            "busqueda_web": _texto(self.busqueda_web),
            "total_estimado": _texto(self.total_estimado),
            "costo_completo": self.costo_completo,
        }


@dataclass
class MetricasInvestigacion:
    """Telemetría de un único intento de investigación, exitoso o
    fallido. Genérica: no conoce nada específico de Anthropic — cada
    proveedor la completa con lo que efectivamente pueda reportar."""

    id_intento: str
    iniciado_en: str
    finalizado_en: str
    duracion_ms: int
    proveedor: str
    modelo: str
    resultado: str  # RESULTADO_OK | RESULTADO_ERROR
    fase_error: str | None = None
    codigo_error: str | None = None
    mensaje_error: str | None = None
    llamadas_logicas_api: int = 0
    reintentos_transporte: int = 0
    stop_reason: str | None = None
    tokens: UsoTokens = field(default_factory=UsoTokens)
    busqueda_web: UsoBusquedaWeb = field(default_factory=UsoBusquedaWeb)
    costos_usd: CostosInvestigacion = field(default_factory=CostosInvestigacion)
    tarifa: TarifaModelo | None = None

    def a_diccionario_json(self) -> dict:
        return {
            "id_intento": self.id_intento,
            "iniciado_en": self.iniciado_en,
            "finalizado_en": self.finalizado_en,
            "duracion_ms": self.duracion_ms,
            "proveedor": self.proveedor,
            "modelo": self.modelo,
            "resultado": self.resultado,
            "fase_error": self.fase_error,
            "codigo_error": self.codigo_error,
            "mensaje_error": self.mensaje_error,
            "llamadas_logicas_api": self.llamadas_logicas_api,
            "reintentos_transporte": self.reintentos_transporte,
            "stop_reason": self.stop_reason,
            "tokens": self.tokens.a_diccionario_json(),
            "busqueda_web": self.busqueda_web.a_diccionario_json(),
            "costos_usd": self.costos_usd.a_diccionario_json(),
            "tarifa": self.tarifa.a_diccionario_json() if self.tarifa is not None else None,
        }


@dataclass
class ResultadoInvestigacion:
    borrador_master: str
    fuentes: list[FuenteInvestigacion] = field(default_factory=list)
    contradicciones_detectadas: list[dict] = field(default_factory=list)
    observaciones: str = ""
    nivel_confianza: str = ""
    metadatos_proveedor: MetadatosProveedor | None = None
    metricas: MetricasInvestigacion | None = None


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
