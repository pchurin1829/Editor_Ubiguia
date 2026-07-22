"""Contrato de Proveedor de Investigación del Motor de Investigación de UBIGUIA.

Un Proveedor de Investigación combina, puertas adentro, un modelo de IA y
un motor de búsqueda (ver decisión C de la especificación). El Motor solo
conoce este contrato, nunca su implementación concreta.
"""
from abc import ABC, abstractmethod

from motor_investigacion.entidad import CandidatoPOI, ContextoEntidad, ResultadoInvestigacion


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
