"""Selección del Proveedor de Investigación activo.

Archivo nuevo y aislado: no modifica proveedor.py, proveedor_simulado.py
ni proveedor_anthropic.py. USAR_PROVEEDOR_REAL es una constante temporal
mientras no exista un selector gráfico de proveedor (fuera de alcance de
esta etapa) — cambiarla a True activa ProveedorInvestigacionAnthropic;
en False (valor por defecto) se sigue usando ProveedorInvestigacionSimulado,
exactamente como en las etapas anteriores.
"""
from motor_investigacion.proveedor import ProveedorInvestigacion
from motor_investigacion.proveedor_anthropic import ProveedorInvestigacionAnthropic
from motor_investigacion.proveedor_simulado import ProveedorInvestigacionSimulado

USAR_PROVEEDOR_REAL = False


def crear_proveedor() -> ProveedorInvestigacion:
    if USAR_PROVEEDOR_REAL:
        return ProveedorInvestigacionAnthropic()
    return ProveedorInvestigacionSimulado()
