"""Proveedor de Investigación simulado.

Sin red, sin credenciales y sin costo — para desarrollo y pruebas del
Motor de Investigación mientras no exista un proveedor real conectado.

Telemetría: también devuelve una MetricasInvestigacion, pero
completamente determinista y en cero (no hay ninguna llamada real que
medir): 0 llamadas a la API, 0 tokens, 0 búsquedas, costo 0. Esto le
permite al Motor y al adaptador de entidad persistir la telemetría de
la misma forma sin importar qué proveedor se haya usado.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from motor_investigacion.entidad import (
    RESULTADO_OK,
    ContextoEntidad,
    CostosInvestigacion,
    FuenteInvestigacion,
    MetadatosProveedor,
    MetricasInvestigacion,
    ResultadoInvestigacion,
    UsoBusquedaWeb,
    UsoTokens,
)
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

        cero = Decimal("0")
        metricas = MetricasInvestigacion(
            id_intento=uuid.uuid4().hex,
            iniciado_en=ahora,
            finalizado_en=ahora,
            duracion_ms=0,
            proveedor=self.nombre,
            modelo=self.modelo,
            resultado=RESULTADO_OK,
            llamadas_logicas_api=0,
            reintentos_transporte=0,
            tokens=UsoTokens(entrada=0, salida=0, cache_escritura=0, cache_lectura=0),
            busqueda_web=UsoBusquedaWeb(
                solicitudes_reportadas=0, busquedas_exitosas=0, busquedas_con_error=0, codigos_error=[]
            ),
            costos_usd=CostosInvestigacion(
                tokens_entrada=cero,
                tokens_salida=cero,
                cache_escritura=cero,
                cache_lectura=cero,
                busqueda_web=cero,
                total_estimado=cero,
                costo_completo=True,
            ),
            tarifa=None,
        )

        return ResultadoInvestigacion(
            borrador_master=borrador,
            fuentes=[fuente],
            contradicciones_detectadas=[],
            observaciones="Contenido de prueba generado por ProveedorInvestigacionSimulado. No usar en producción.",
            nivel_confianza="BAJO",
            metadatos_proveedor=MetadatosProveedor(nombre=self.nombre, modelo=self.modelo),
            metricas=metricas,
        )
