"""Proveedor de Investigación real, conectado a la API de Anthropic.

Implementa exactamente el mismo contrato que ProveedorInvestigacionSimulado
(ver proveedor.py): el resto del sistema (Motor, UI) no sabe ni necesita
saber qué proveedor está usando.

Etapa 5: prompt mínimo de prueba únicamente, para verificar la conexión
de punta a punta. No hay búsqueda web todavía, así que fuentes.md queda
marcado honestamente como una prueba de conectividad, no como una fuente
de investigación real. El prompt definitivo se implementará en una etapa
posterior.

Etapa 6: el texto del prompt ya no está escrito en este archivo — se
carga desde Docs/prompts/ vía motor_investigacion/prompts.py. Ningún
prompt importante queda hardcodeado en el proveedor.
"""
import os
from datetime import datetime

import anthropic

from motor_investigacion.entidad import ContextoEntidad, FuenteInvestigacion, ResultadoInvestigacion
from motor_investigacion.prompts import PromptNoEncontradoError, cargar_prompt
from motor_investigacion.proveedor import ProveedorInvestigacion

# Constante única y fácilmente modificable: el modelo no queda escrito
# en ningún otro lugar del proveedor.
DEFAULT_MODEL = "claude-opus-4-8"

MAX_TOKENS_PRUEBA = 512

# Nombre del archivo de prompt en Docs/prompts/. No hay ningún prompt
# de respaldo interno: si el archivo no existe, cargar_prompt() lanza
# PromptNoEncontradoError (ver _construir_prompt_prueba).
NOMBRE_PROMPT_INVESTIGACION = "PROMPT_INVESTIGACION_v1.md"


class ErrorProveedorAnthropic(Exception):
    """Error claro pensado para mostrarse al editor en la UI.

    Nunca se debe mostrar un traceback crudo de la API: cualquier error
    de anthropic (autenticación, límite de uso, timeout, conexión,
    HTTP) se convierte en una instancia de esta excepción con un
    mensaje entendible."""


class ProveedorInvestigacionAnthropic(ProveedorInvestigacion):
    # Mismo patrón que ProveedorInvestigacionSimulado: nombre/modelo son
    # atributos de clase, sin __init__ propio, para no agregar ningún
    # método público nuevo al contrato de ProveedorInvestigacion.
    nombre = "anthropic"
    modelo = DEFAULT_MODEL

    def _crear_cliente(self) -> anthropic.Anthropic:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ErrorProveedorAnthropic(
                "No se encontró la variable de entorno ANTHROPIC_API_KEY. "
                "Configurala antes de usar el proveedor de Anthropic."
            )
        return anthropic.Anthropic(api_key=api_key)

    def _construir_prompt_prueba(self, contexto: ContextoEntidad) -> str:
        try:
            prompt_base = cargar_prompt(NOMBRE_PROMPT_INVESTIGACION)
        except PromptNoEncontradoError as exc:
            raise ErrorProveedorAnthropic(str(exc)) from exc
        return f"{prompt_base}\n\nNombre del POI: {contexto.nombre}"

    def investigar_entidad(self, contexto: ContextoEntidad) -> ResultadoInvestigacion:
        cliente = self._crear_cliente()
        prompt = self._construir_prompt_prueba(contexto)

        try:
            respuesta = cliente.messages.create(
                model=self.modelo,
                max_tokens=MAX_TOKENS_PRUEBA,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AuthenticationError as exc:
            raise ErrorProveedorAnthropic(
                "La API Key de Anthropic no es válida (error de autenticación)."
            ) from exc
        except anthropic.RateLimitError as exc:
            raise ErrorProveedorAnthropic(
                "Se alcanzó el límite de uso de la API de Anthropic. Intentá de nuevo más tarde."
            ) from exc
        except anthropic.APITimeoutError as exc:
            raise ErrorProveedorAnthropic(
                "La API de Anthropic no respondió a tiempo (timeout)."
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise ErrorProveedorAnthropic(
                "No se pudo conectar con la API de Anthropic. Verificá la conexión a Internet."
            ) from exc
        except anthropic.APIStatusError as exc:
            raise ErrorProveedorAnthropic(
                f"La API de Anthropic devolvió un error HTTP ({exc.status_code})."
            ) from exc
        except anthropic.APIError as exc:
            raise ErrorProveedorAnthropic(f"Error inesperado de la API de Anthropic: {exc}") from exc

        texto_respuesta = "".join(
            bloque.text for bloque in respuesta.content if getattr(bloque, "type", None) == "text"
        ).strip()
        if not texto_respuesta:
            raise ErrorProveedorAnthropic("La API de Anthropic devolvió una respuesta vacía.")

        return self._armar_resultado(contexto, texto_respuesta)

    def _armar_resultado(self, contexto: ContextoEntidad, texto_respuesta: str) -> ResultadoInvestigacion:
        ahora = datetime.now().isoformat(timespec="seconds")

        borrador = (
            "# POI MASTER\n\n"
            f"# {contexto.nombre}\n\n"
            "## 1. Identificación\n\n"
            f"Nombre: {contexto.nombre}\n\n"
            "## 2. Descripción General\n\n"
            f"> Generado por ProveedorInvestigacionAnthropic — prompt de prueba (Etapa 5), "
            f"modelo {self.modelo}.\n\n"
            f"{texto_respuesta}\n\n"
            "## 3. Historia\n\n"
            "## 4. Qué observar\n\n"
            "## 5. Curiosidades\n\n"
            "## 6. Información útil\n\n"
            "## 7. Resumen para audio\n\n"
            "## 8. POIs relacionados\n\n"
            "## 9. Palabras clave\n\n"
            "## 10. Fuentes\n\n"
            "(Prompt de prueba: todavía no se realizó búsqueda de fuentes reales.)\n"
        )

        fuente_prueba = FuenteInvestigacion(
            titulo="Prueba de conexión con la API de Anthropic",
            url="",
            sitio="Motor de Investigación de UBIGUIA — prueba de conectividad",
            consultado_en=ahora,
            secciones_respaldadas=[],
            confianza="prueba",
            notas=(
                "Este registro no es una fuente real de investigación: confirma que "
                "ProveedorInvestigacionAnthropic pudo conectarse a la API de Anthropic "
                f"(modelo {self.modelo}) y generar contenido. La búsqueda de fuentes "
                "reales se implementará en una etapa posterior."
            ),
            contradicciones=[],
        )

        return ResultadoInvestigacion(
            borrador_master=borrador,
            fuentes=[fuente_prueba],
            contradicciones_detectadas=[],
        )
