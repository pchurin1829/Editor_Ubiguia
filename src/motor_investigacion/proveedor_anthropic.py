"""Proveedor de Investigación real, conectado a la API de Anthropic.

Implementa exactamente el mismo contrato que ProveedorInvestigacionSimulado
(ver proveedor.py): el resto del sistema (Motor, UI) no sabe ni necesita
saber qué proveedor está usando.

Paso 4: el proveedor pide al modelo una respuesta estructurada (JSON) que
contiene el borrador completo del POI_MASTER_BORRADOR.md junto con
fuentes, contradicciones, observaciones y nivel de confianza, y valida
esa estructura antes de convertirla en un ResultadoInvestigacion. La
estructura editorial del borrador (títulos, orden de secciones, criterios
de redacción) la define exclusivamente el Prompt Maestro cargado desde
disco — este archivo no la redacta ni la reescribe, solo valida que las
secciones numeradas obligatorias estén presentes.

Todavía no hay búsqueda web real: el modelo responde en base a su
conocimiento general. Esa capacidad se agrega en una etapa posterior.
"""
import json
import os
import re

import anthropic

from motor_investigacion.entidad import (
    NIVELES_CONFIANZA_VALIDOS,
    ContextoEntidad,
    FuenteInvestigacion,
    MetadatosProveedor,
    ResultadoInvestigacion,
)
from motor_investigacion.prompts import PromptNoEncontradoError, cargar_prompt
from motor_investigacion.proveedor import ProveedorInvestigacion

# Constante única y fácilmente modificable: el modelo no queda escrito
# en ningún otro lugar del proveedor.
DEFAULT_MODEL = "claude-opus-4-8"

# El borrador estructurado (13 secciones + fuentes + control de calidad)
# es sustancialmente más largo que la respuesta de prueba de etapas
# anteriores.
MAX_TOKENS_RESPUESTA = 4096

# Nombre del archivo de prompt en Docs/prompts/. No hay ningún prompt
# de respaldo interno: si el archivo no existe, cargar_prompt() lanza
# PromptNoEncontradoError (ver _construir_prompt).
NOMBRE_PROMPT_INVESTIGACION = "PROMPT_MAESTRO_INVESTIGACION_v1.0.md"

# Cantidad de secciones numeradas obligatorias definidas por la
# estructura del POI_MASTER_BORRADOR.md en el Prompt Maestro operativo
# (sección 13). Solo se valida la numeración: los títulos y el contenido
# de cada sección los define el propio Prompt Maestro, no este archivo.
CANTIDAD_SECCIONES_OBLIGATORIAS = 13

# Instrucción técnica de formato de respuesta. No redefine la estructura
# editorial del Prompt Maestro (esa la define exclusivamente el propio
# Prompt Maestro): solo indica el sobre JSON en el que debe viajar.
_INSTRUCCION_FORMATO_RESPUESTA = """

---

Formato de la respuesta (obligatorio):

Respondé ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después, con exactamente estas claves:

- "borrador_markdown": el POI_MASTER_BORRADOR.md completo en Markdown, siguiendo la estructura obligatoria definida en este Prompt Maestro.
- "fuentes": lista de objetos; cada uno con las claves "titulo", "url", "sitio", "consultado_en", "secciones_respaldadas" (lista), "confianza", "notas" e "identificador", cuando estén disponibles.
- "contradicciones": lista de objetos; cada uno con las claves "topic", "sources" (lista) y "detail".
- "observaciones": texto libre con las observaciones para el editor (sección 13, "Observaciones para el editor").
- "nivel_confianza": uno de "ALTO", "MEDIO" o "BAJO" (nivel de confianza general, sección 13).
"""


class ErrorProveedorAnthropic(Exception):
    """Error claro pensado para mostrarse al editor en la UI.

    Nunca se debe mostrar un traceback crudo de la API: cualquier error
    de anthropic (autenticación, límite de uso, timeout, conexión,
    HTTP), de formato JSON o de estructura de la respuesta se convierte
    en una instancia de esta excepción con un mensaje entendible."""


def _validar_secciones_obligatorias(borrador: str) -> None:
    faltantes = [
        numero
        for numero in range(1, CANTIDAD_SECCIONES_OBLIGATORIAS + 1)
        if not re.search(rf"##\s*{numero}\.", borrador)
    ]
    if faltantes:
        raise ErrorProveedorAnthropic(
            "El borrador de la respuesta no incluye todas las secciones numeradas obligatorias "
            f"del Prompt Maestro (faltan: {', '.join(str(n) for n in faltantes)})."
        )


def _validar_lista_de_objetos(valor, nombre_campo: str) -> None:
    if not isinstance(valor, list):
        raise ErrorProveedorAnthropic(f"El campo '{nombre_campo}' de la respuesta debe ser una lista.")
    for elemento in valor:
        if not isinstance(elemento, dict):
            raise ErrorProveedorAnthropic(f"Cada elemento de '{nombre_campo}' debe ser un objeto JSON.")


def _validar_respuesta_estructurada(datos) -> None:
    if not isinstance(datos, dict):
        raise ErrorProveedorAnthropic("La respuesta de la API de Anthropic no es un objeto JSON.")

    claves_obligatorias = ("borrador_markdown", "fuentes", "contradicciones", "observaciones", "nivel_confianza")
    faltantes = [clave for clave in claves_obligatorias if clave not in datos]
    if faltantes:
        raise ErrorProveedorAnthropic(
            "La respuesta de la API de Anthropic no tiene la estructura esperada: "
            f"faltan las claves {', '.join(faltantes)}."
        )

    borrador = datos["borrador_markdown"]
    if not isinstance(borrador, str) or not borrador.strip():
        raise ErrorProveedorAnthropic("El campo 'borrador_markdown' de la respuesta está vacío o no es texto.")
    if "#" not in borrador:
        raise ErrorProveedorAnthropic("El campo 'borrador_markdown' de la respuesta no parece contener Markdown.")
    _validar_secciones_obligatorias(borrador)

    _validar_lista_de_objetos(datos["fuentes"], "fuentes")
    for fuente in datos["fuentes"]:
        secciones = fuente.get("secciones_respaldadas")
        if secciones is not None and not isinstance(secciones, list):
            raise ErrorProveedorAnthropic("El campo 'secciones_respaldadas' de una fuente debe ser una lista.")

    _validar_lista_de_objetos(datos["contradicciones"], "contradicciones")
    for contradiccion in datos["contradicciones"]:
        fuentes_asociadas = contradiccion.get("sources")
        if fuentes_asociadas is not None and not isinstance(fuentes_asociadas, list):
            raise ErrorProveedorAnthropic("El campo 'sources' de una contradicción debe ser una lista.")

    if not isinstance(datos["observaciones"], str):
        raise ErrorProveedorAnthropic("El campo 'observaciones' de la respuesta debe ser texto.")

    if datos["nivel_confianza"] not in NIVELES_CONFIANZA_VALIDOS:
        raise ErrorProveedorAnthropic(
            f"El campo 'nivel_confianza' de la respuesta debe ser uno de {NIVELES_CONFIANZA_VALIDOS} "
            f"(se recibió: {datos['nivel_confianza']!r})."
        )


def _fuente_desde_diccionario(datos_fuente: dict) -> FuenteInvestigacion:
    return FuenteInvestigacion(
        titulo=str(datos_fuente.get("titulo", "")),
        url=str(datos_fuente.get("url", "")),
        sitio=str(datos_fuente.get("sitio", "")),
        consultado_en=str(datos_fuente.get("consultado_en", "")),
        secciones_respaldadas=list(datos_fuente.get("secciones_respaldadas") or []),
        confianza=str(datos_fuente.get("confianza", "")),
        notas=str(datos_fuente.get("notas", "")),
        identificador=str(datos_fuente.get("identificador", "")),
    )


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

    def _construir_prompt(self, contexto: ContextoEntidad) -> str:
        try:
            prompt_base = cargar_prompt(NOMBRE_PROMPT_INVESTIGACION)
        except PromptNoEncontradoError as exc:
            raise ErrorProveedorAnthropic(str(exc)) from exc
        return f"{prompt_base}\n\nNombre del POI: {contexto.nombre}{_INSTRUCCION_FORMATO_RESPUESTA}"

    def investigar_entidad(self, contexto: ContextoEntidad) -> ResultadoInvestigacion:
        cliente = self._crear_cliente()
        prompt = self._construir_prompt(contexto)

        try:
            respuesta = cliente.messages.create(
                model=self.modelo,
                max_tokens=MAX_TOKENS_RESPUESTA,
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

        try:
            datos = json.loads(texto_respuesta)
        except json.JSONDecodeError as exc:
            raise ErrorProveedorAnthropic("La respuesta de la API de Anthropic no es un JSON válido.") from exc

        _validar_respuesta_estructurada(datos)

        return self._resultado_desde_respuesta(datos)

    def _resultado_desde_respuesta(self, datos: dict) -> ResultadoInvestigacion:
        return ResultadoInvestigacion(
            borrador_master=datos["borrador_markdown"],
            fuentes=[_fuente_desde_diccionario(f) for f in datos["fuentes"]],
            contradicciones_detectadas=list(datos["contradicciones"]),
            observaciones=datos["observaciones"],
            nivel_confianza=datos["nivel_confianza"],
            metadatos_proveedor=MetadatosProveedor(nombre=self.nombre, modelo=self.modelo),
        )
