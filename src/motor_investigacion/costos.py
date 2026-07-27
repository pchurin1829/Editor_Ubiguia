"""Tarifas oficiales de Anthropic y cálculo de costos estimados.

Módulo aislado: centraliza los valores monetarios en un único lugar,
fechados y con referencia a la documentación oficial, para poder
actualizarlos sin tocar el Motor ni ningún proveedor concreto.

Tarifas consultadas en la documentación oficial de Anthropic
(https://platform.claude.com/docs/en/about-claude/pricing), verificada
el 2026-07-26.

Todo el cálculo usa `Decimal` (nunca `float`) para evitar errores de
precisión en valores monetarios. El costo se calcula únicamente a
partir de métricas efectivamente reportadas por la API: si falta un
dato, el componente correspondiente queda en `None` y el resultado se
marca como parcial (`costo_completo=False`) en vez de completarse con
una estimación inventada.
"""
from dataclasses import dataclass
from decimal import Decimal

from motor_investigacion.entidad import CostosInvestigacion, UsoBusquedaWeb, UsoTokens

UN_MILLON = Decimal("1000000")

# Precisión de los valores monetarios calculados (en USD).
_PRECISION_USD = Decimal("0.000001")


@dataclass(frozen=True)
class TarifaModeloConfigurada:
    """Tarifa oficial de un modelo, vigente en un rango de fechas
    determinado. `vigente_hasta` es None cuando la tarifa sigue vigente
    (no tiene fecha de fin anunciada todavía)."""

    modelo: str
    vigente_desde: str
    vigente_hasta: str | None
    moneda: str
    fuente: str
    entrada_por_millon: Decimal
    salida_por_millon: Decimal
    cache_escritura_5m_por_millon: Decimal | None
    cache_lectura_por_millon: Decimal | None
    busqueda_web_por_busqueda: Decimal


class TarifaNoDisponibleError(Exception):
    """No hay ninguna tarifa configurada para el modelo indicado."""


# Tabla versionada de tarifas por modelo. Cada entrada es la tarifa
# ACTUALMENTE vigente para ese modelo — cuando una tarifa cambie (por
# ejemplo, el fin del precio introductorio de Sonnet 5 el 2026-08-31),
# agregar una entrada nueva con su propia vigencia en vez de modificar
# esta, para conservar trazabilidad de qué tarifa se usó en cada intento
# ya registrado.
TARIFAS_POR_MODELO: dict[str, TarifaModeloConfigurada] = {
    "claude-sonnet-5": TarifaModeloConfigurada(
        modelo="claude-sonnet-5",
        vigente_desde="2026-01-01",
        vigente_hasta="2026-08-31",
        moneda="USD",
        fuente=(
            "https://platform.claude.com/docs/en/about-claude/pricing "
            "(precio introductorio de Claude Sonnet 5, vigente hasta el 2026-08-31; "
            "consultado el 2026-07-26)"
        ),
        entrada_por_millon=Decimal("2.00"),
        salida_por_millon=Decimal("10.00"),
        cache_escritura_5m_por_millon=Decimal("2.50"),
        cache_lectura_por_millon=Decimal("0.20"),
        busqueda_web_por_busqueda=Decimal("10.00") / Decimal("1000"),
    ),
}


def obtener_tarifa(modelo: str) -> TarifaModeloConfigurada:
    """Devuelve la tarifa configurada para `modelo`. Lanza
    TarifaNoDisponibleError si no hay ninguna — nunca inventa una
    tarifa por aproximación con otro modelo."""
    tarifa = TARIFAS_POR_MODELO.get(modelo)
    if tarifa is None:
        raise TarifaNoDisponibleError(f"No hay tarifa configurada para el modelo '{modelo}'.")
    return tarifa


def _costo_por_tokens(cantidad: int | None, tarifa_por_millon: Decimal | None) -> Decimal | None:
    if cantidad is None or tarifa_por_millon is None:
        return None
    return (Decimal(cantidad) * tarifa_por_millon / UN_MILLON).quantize(_PRECISION_USD)


def calcular_costos(
    tokens: UsoTokens, busqueda_web: UsoBusquedaWeb, tarifa: TarifaModeloConfigurada
) -> CostosInvestigacion:
    """Calcula el costo estimado en USD a partir únicamente de métricas
    reportadas por la API. Una búsqueda web con error nunca se
    considera facturable (se cobra por `busquedas_exitosas`, no por
    `solicitudes_reportadas`), según la documentación oficial: "If an
    error occurs during web search, the web search will not be
    billed"."""
    costo_entrada = _costo_por_tokens(tokens.entrada, tarifa.entrada_por_millon)
    costo_salida = _costo_por_tokens(tokens.salida, tarifa.salida_por_millon)
    costo_cache_escritura = _costo_por_tokens(tokens.cache_escritura, tarifa.cache_escritura_5m_por_millon)
    costo_cache_lectura = _costo_por_tokens(tokens.cache_lectura, tarifa.cache_lectura_por_millon)

    if busqueda_web.busquedas_exitosas is None:
        costo_busqueda = None
    else:
        costo_busqueda = (
            Decimal(busqueda_web.busquedas_exitosas) * tarifa.busqueda_web_por_busqueda
        ).quantize(_PRECISION_USD)

    componentes = (costo_entrada, costo_salida, costo_cache_escritura, costo_cache_lectura, costo_busqueda)
    costo_completo = all(componente is not None for componente in componentes)
    total_estimado = sum(componentes, Decimal("0")).quantize(_PRECISION_USD) if costo_completo else None

    return CostosInvestigacion(
        tokens_entrada=costo_entrada,
        tokens_salida=costo_salida,
        cache_escritura=costo_cache_escritura,
        cache_lectura=costo_cache_lectura,
        busqueda_web=costo_busqueda,
        total_estimado=total_estimado,
        costo_completo=costo_completo,
    )
