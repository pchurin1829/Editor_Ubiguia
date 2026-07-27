"""Contrato de Proveedor de Investigación del Motor de Investigación de UBIGUIA.

Un Proveedor de Investigación combina, puertas adentro, un modelo de IA y
un motor de búsqueda (ver decisión C de la especificación). El Motor solo
conoce este contrato, nunca su implementación concreta.
"""
from abc import ABC, abstractmethod

from motor_investigacion.entidad import CandidatoPOI, ContextoEntidad, MetricasInvestigacion, ResultadoInvestigacion


class ErrorProveedorInvestigacion(Exception):
    """Error genérico de un Proveedor de Investigación.

    El Motor solo conoce esta clase base — nunca una implementación
    concreta de proveedor (por ejemplo `ErrorProveedorAnthropic`) — para
    no romper el aislamiento entre el Motor y el proveedor. Puede llevar
    adjunta la telemetría del intento fallido (`.metricas`) para que el
    Motor la persista en `_research/metricas.json` aunque la
    investigación no haya terminado con éxito. `.metricas` queda en
    `None` si el proveedor no llegó a recopilar ningún dato."""

    def __init__(self, mensaje: str, *, fase: str | None = None, codigo: str | None = None):
        super().__init__(mensaje)
        self.fase = fase
        self.codigo = codigo
        self.metricas: MetricasInvestigacion | None = None


class ProveedorInvestigacion(ABC):
    nombre: str = "desconocido"
    modelo: str = "desconocido"

    @abstractmethod
    def investigar_entidad(self, contexto: ContextoEntidad) -> ResultadoInvestigacion:
        """Investiga una entidad existente. Debe devolver un resultado
        completo o lanzar una excepción — nunca un resultado parcial."""

    def descubrir_entidades(self, alcance: dict) -> list[CandidatoPOI]:
        """Propone entidades candidatas dentro de un alcance.

        No implementado en la Etapa 1 del Motor de Investigación."""
        raise NotImplementedError("El descubrimiento de entidades no está implementado en esta etapa.")
