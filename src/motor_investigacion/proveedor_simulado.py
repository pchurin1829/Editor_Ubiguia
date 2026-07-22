"""Proveedor de Investigación simulado.

Sin red, sin credenciales y sin costo — para desarrollo y pruebas del
Motor de Investigación mientras no exista un proveedor real conectado.
"""
from datetime import datetime

from motor_investigacion.entidad import ContextoEntidad, FuenteInvestigacion, ResultadoInvestigacion
from motor_investigacion.proveedor import ProveedorInvestigacion


class ProveedorInvestigacionSimulado(ProveedorInvestigacion):
    nombre = "simulado"
    modelo = "mock-1"

    def investigar_entidad(self, contexto: ContextoEntidad) -> ResultadoInvestigacion:
        ahora = datetime.now().isoformat(timespec="seconds")
        geo = contexto.contexto_geografico

        fuente = FuenteInvestigacion(
            titulo=f"Fuente simulada para {contexto.nombre}",
            url="https://ejemplo.invalid/fuente-simulada",
            sitio="Proveedor de Investigación Simulado",
            consultado_en=ahora,
            secciones_respaldadas=["2. Descripción General", "3. Historia"],
            confianza="baja",
            notas="Contenido de prueba generado por ProveedorInvestigacionSimulado. No usar en producción.",
            contradicciones=[],
        )

        borrador = (
            "# POI MASTER\n\n"
            f"# {contexto.nombre}\n\n"
            "## 1. Identificación\n\n"
            f"Nombre: {contexto.nombre}\n"
            f"Ciudad: {geo.get('ciudad', '')}\n"
            f"Provincia: {geo.get('provincia', '')}\n"
            f"País: {geo.get('pais', '')}\n"
            f"Categoría: {geo.get('categoria', '')}\n\n"
            "## 2. Descripción General\n\n"
            "Borrador de prueba generado por el Proveedor de Investigación Simulado, "
            "sin conexión a ninguna fuente real.\n\n"
            "## 3. Historia\n\n"
            "(Contenido de prueba.)\n\n"
            "## 4. Qué observar\n\n"
            "## 5. Curiosidades\n\n"
            "## 6. Información útil\n\n"
            "## 7. Resumen para audio\n\n"
            "## 8. POIs relacionados\n\n"
            "## 9. Palabras clave\n\n"
            "## 10. Fuentes\n\n"
            f"- {fuente.titulo} ({fuente.url})\n"
        )

        return ResultadoInvestigacion(
            borrador_master=borrador,
            fuentes=[fuente],
            contradicciones_detectadas=[],
        )
