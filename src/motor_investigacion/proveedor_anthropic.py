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

Paso 5A: la misma llamada ahora incluye la herramienta oficial de
búsqueda web del SDK de Anthropic (`web_search_20250305`, mecanismo
estable — ver documentación oficial "Web search tool"). Es una
"server tool": la API ejecuta la búsqueda del lado del servidor dentro
de la misma llamada a messages.create(), sin que este proveedor tenga
que orquestar un segundo round-trip. El modelo decide si busca o no; si
busca, los resultados reales quedan disponibles para que el modelo los
use al construir el JSON de respuesta (en particular el campo
"fuentes"). Si la herramienta de búsqueda falla (límite de usos, límite
de uso general, consulta inválida, etc.), la API igual responde 200 con
el error embebido en un bloque `web_search_tool_result`; ese caso se
detecta y se traduce a ErrorProveedorAnthropic antes de intentar
interpretar el resto de la respuesta.

Paso 5A.2: primera validación real controlada por costo — modelo
`claude-sonnet-5`, `max_retries=0` (sin reintentos automáticos del SDK)
y `MAX_USOS_BUSQUEDA_WEB=3` (como mucho tres búsquedas por investigación;
subido desde 1 tras comprobar que una sola búsqueda agota el límite con
`max_uses_exceeded` antes de completar la investigación). `thinking`
queda deshabilitado explícitamente: `claude-sonnet-5` usa thinking
adaptativo por defecto, y en las primeras validaciones reales ese
thinking consumía casi todo `MAX_TOKENS_RESPUESTA` (la salida escalaba
casi 1:1 con el límite) sin dejar espacio para completar el JSON de
respuesta, cortando siempre en `stop_reason=max_tokens`.

Telemetría y costos: cada llamada a investigar_entidad() recopila una
MetricasInvestigacion (ver entidad.py) — duración, llamadas lógicas,
tokens, uso de caché, búsquedas web y costo estimado (ver costos.py) —
tanto si la investigación termina en éxito como si falla en cualquier
punto (antes de llamar a la API, durante la llamada HTTP, o después de
recibir una respuesta pero con un error de validación). El proveedor
nunca escribe esa telemetría a disco: solo la recopila y la adjunta al
resultado (éxito) o a la excepción (error), para que el Motor sea quien
decida cómo y dónde persistirla.
"""
import json
import os
import re
import time
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from motor_investigacion import costos
from motor_investigacion.entidad import (
    NIVELES_CONFIANZA_VALIDOS,
    RESULTADO_ERROR,
    RESULTADO_OK,
    ContextoEntidad,
    CostosInvestigacion,
    FuenteInvestigacion,
    MetadatosProveedor,
    MetricasInvestigacion,
    ResultadoInvestigacion,
    TarifaModelo,
    UsoBusquedaWeb,
    UsoTokens,
)
from motor_investigacion.prompts import PromptNoEncontradoError, cargar_prompt
from motor_investigacion.proveedor import ErrorProveedorInvestigacion, ProveedorInvestigacion

# Configuración local: `.env.local` vive en la raíz del proyecto (tres
# niveles arriba de este archivo: src/motor_investigacion/ -> src/ ->
# raíz) y está excluido de git (ver .gitignore). Nunca se loguea su
# ruta ni su contenido.
_RUTA_ENV_LOCAL = Path(__file__).resolve().parents[2] / ".env.local"


def _cargar_env_local() -> None:
    """Carga variables desde `.env.local` sin pisar las que ya existan
    en el entorno del proceso (override=False): una variable configurada
    a nivel de sistema/usuario sigue teniendo prioridad. Si el archivo
    no existe, no hace nada (no es un error)."""
    load_dotenv(_RUTA_ENV_LOCAL, override=False)


_cargar_env_local()

# Constante única y fácilmente modificable: el modelo no queda escrito
# en ningún otro lugar del proveedor.
DEFAULT_MODEL = "claude-sonnet-5"

# El borrador estructurado (13 secciones + fuentes + control de calidad)
# es sustancialmente más largo que la respuesta de prueba de etapas
# anteriores. 4096, 8192 y 16000 resultaron insuficientes en la validación
# real (Paso 5A.2): la respuesta cortó siempre en stop_reason=max_tokens,
# con la salida pegada al límite en cada intento (4250, 8578 y 16333
# tokens) — incluso con thinking deshabilitado. 21000 es el máximo que
# admite el SDK sin pasar a streaming para este modelo (por encima de
# ~21500 el SDK exige streaming por riesgo de timeout HTTP en una
# respuesta no streameada tan larga); se usa ese tope para no cambiar el
# mecanismo de la llamada (create() síncrono) que asumen las pruebas
# existentes.
MAX_TOKENS_RESPUESTA = 21000

# Nombre del archivo de prompt en Docs/prompts/. No hay ningún prompt
# de respaldo interno: si el archivo no existe, cargar_prompt() lanza
# PromptNoEncontradoError (ver _construir_prompt).
NOMBRE_PROMPT_INVESTIGACION = "PROMPT_MAESTRO_INVESTIGACION_v1.0.md"

# Cantidad de secciones numeradas obligatorias definidas por la
# estructura del POI_MASTER_BORRADOR.md en el Prompt Maestro operativo
# (sección 13). Solo se valida la numeración: los títulos y el contenido
# de cada sección los define el propio Prompt Maestro, no este archivo.
CANTIDAD_SECCIONES_OBLIGATORIAS = 13

# Herramienta oficial de búsqueda web del SDK de Anthropic (mecanismo
# estable, no beta: vive en anthropic.types, no en anthropic.types.beta).
# Se usa la versión básica "web_search_20250305": las versiones más
# nuevas (20260209, 20260318) agregan filtrado dinámico y control de
# inclusión de respuesta que no se necesitan en esta etapa.
TIPO_HERRAMIENTA_BUSQUEDA_WEB = "web_search_20250305"
NOMBRE_HERRAMIENTA_BUSQUEDA_WEB = "web_search"

# Paso 5A.2: subido de 1 a 3 tras comprobar que una sola búsqueda agota
# el límite (`max_uses_exceeded`) antes de completar la investigación.
# Se reevaluará en el Paso 5B (investigación completa) si corresponde
# aumentar este límite.
MAX_USOS_BUSQUEDA_WEB = 3

# Structured Outputs (output_config.format del SDK): esquema JSON que le
# garantiza a la API la forma exacta que espera _resultado_desde_respuesta(),
# en vez de depender únicamente de instrucciones textuales para "producir
# JSON válido" (mecanismo que en la validación real terminó devolviendo un
# JSON inválido pese a stop_reason=end_turn). Los campos de cada fuente
# se declaran como string simple (no nullable): cuando el dato no está
# disponible, el contrato ya espera cadena vacía, no `null` — un valor
# `null` ahí rompería _fuente_desde_diccionario(), que hace str(...) sobre
# cada campo.
ESQUEMA_FUENTE = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "url": {"type": "string"},
        "sitio": {"type": "string"},
        "consultado_en": {"type": "string"},
        "secciones_respaldadas": {"type": "array", "items": {"type": "string"}},
        "confianza": {"type": "string"},
        "notas": {"type": "string"},
        "identificador": {"type": "string"},
    },
    "required": [
        "titulo",
        "url",
        "sitio",
        "consultado_en",
        "secciones_respaldadas",
        "confianza",
        "notas",
        "identificador",
    ],
    "additionalProperties": False,
}

ESQUEMA_CONTRADICCION = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "detail": {"type": "string"},
    },
    "required": ["topic", "sources", "detail"],
    "additionalProperties": False,
}

ESQUEMA_RESPUESTA_ESTRUCTURADA = {
    "type": "object",
    "properties": {
        "borrador_markdown": {"type": "string"},
        "fuentes": {"type": "array", "items": ESQUEMA_FUENTE},
        "contradicciones": {"type": "array", "items": ESQUEMA_CONTRADICCION},
        "observaciones": {"type": "string"},
        "nivel_confianza": {"type": "string", "enum": list(NIVELES_CONFIANZA_VALIDOS)},
    },
    "required": ["borrador_markdown", "fuentes", "contradicciones", "observaciones", "nivel_confianza"],
    "additionalProperties": False,
}

# Fases posibles de MetricasInvestigacion.fase_error para este proveedor.
FASE_ANTES_DE_LLAMAR = "ANTES_DE_LLAMAR"
FASE_LLAMADA_HTTP = "LLAMADA_HTTP"
FASE_VALIDACION_BUSQUEDA_WEB = "VALIDACION_BUSQUEDA_WEB"
FASE_RESPUESTA_VACIA = "RESPUESTA_VACIA"
FASE_PARSEO_JSON = "PARSEO_JSON"
FASE_VALIDACION_ESTRUCTURA = "VALIDACION_ESTRUCTURA"

# Instrucción técnica de formato de respuesta. No redefine la estructura
# editorial del Prompt Maestro (esa la define exclusivamente el propio
# Prompt Maestro): solo describe el contenido de cada clave del sobre
# JSON. La validez estructural del JSON en sí (que sea JSON, que tenga
# exactamente estas claves) ya no depende de esta instrucción textual:
# la garantiza output_config.format (ESQUEMA_RESPUESTA_ESTRUCTURADA) a
# nivel de API, así que se retiró la orden redundante de "respondé
# ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después".
_INSTRUCCION_FORMATO_RESPUESTA = """

---

Formato de la respuesta (obligatorio):

La respuesta debe tener estas claves:

- "borrador_markdown": el POI_MASTER_BORRADOR.md completo en Markdown, siguiendo la estructura obligatoria definida en este Prompt Maestro.
- "fuentes": lista de objetos; cada uno con las claves "titulo", "url", "sitio", "consultado_en", "secciones_respaldadas" (lista), "confianza", "notas" e "identificador", cuando estén disponibles.
- "contradicciones": lista de objetos; cada uno con las claves "topic", "sources" (lista) y "detail".
- "observaciones": texto libre con las observaciones para el editor (sección 13, "Observaciones para el editor").
- "nivel_confianza": uno de "ALTO", "MEDIO" o "BAJO" (nivel de confianza general, sección 13).
"""


class ErrorProveedorAnthropic(ErrorProveedorInvestigacion):
    """Error claro pensado para mostrarse al editor en la UI.

    Nunca se debe mostrar un traceback crudo de la API: cualquier error
    de anthropic (autenticación, límite de uso, timeout, conexión,
    HTTP), de formato JSON o de estructura de la respuesta se convierte
    en una instancia de esta excepción con un mensaje entendible.

    Hereda de ErrorProveedorInvestigacion (`proveedor.py`): el atributo
    `.metricas`, cuando se pudo recopilar telemetría del intento antes
    de fallar, viaja con la excepción para que el Motor la persista."""


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


def _validar_sin_errores_de_busqueda_web(respuesta) -> None:
    """La herramienta de búsqueda web reporta sus errores (límite de
    usos, límite de uso general, consulta inválida, etc.) embebidos
    dentro de un bloque `web_search_tool_result` de una respuesta 200,
    no como una excepción HTTP. Si eso ocurre, se traduce a
    ErrorProveedorAnthropic antes de intentar interpretar el resto de
    la respuesta como el JSON esperado."""
    for bloque in respuesta.content:
        if getattr(bloque, "type", None) != "web_search_tool_result":
            continue
        contenido = bloque.content
        codigo_error = getattr(contenido, "error_code", None)
        if codigo_error:
            raise ErrorProveedorAnthropic(
                f"La búsqueda web de Anthropic falló ({codigo_error}).",
                fase=FASE_VALIDACION_BUSQUEDA_WEB,
                codigo=codigo_error,
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


def _extraer_uso_tokens(respuesta) -> UsoTokens:
    """Lee los tokens reportados por la API desde `respuesta.usage`
    (tipo real `anthropic.types.Usage`, verificado contra el SDK
    instalado: `input_tokens`, `output_tokens`,
    `cache_creation_input_tokens`, `cache_read_input_tokens`). Si el
    objeto `usage` no está presente, todos los campos quedan en None."""
    uso = getattr(respuesta, "usage", None)
    if uso is None:
        return UsoTokens()
    return UsoTokens(
        entrada=getattr(uso, "input_tokens", None),
        salida=getattr(uso, "output_tokens", None),
        cache_escritura=getattr(uso, "cache_creation_input_tokens", None),
        cache_lectura=getattr(uso, "cache_read_input_tokens", None),
    )


def _extraer_uso_busqueda_web(respuesta) -> UsoBusquedaWeb:
    """Combina dos fuentes: `respuesta.usage.server_tool_use.web_search_requests`
    (tipo real `anthropic.types.ServerToolUsage`, verificado contra el
    SDK instalado) para la cantidad de solicitudes reportadas por la
    propia API, y los bloques `web_search_tool_result` del contenido
    para distinguir cuántas terminaron con resultados (facturables)
    de cuántas terminaron con error (no facturables, según la
    documentación oficial de Web Search: "If an error occurs during
    web search, the web search will not be billed")."""
    uso = getattr(respuesta, "usage", None)
    uso_herramientas_servidor = getattr(uso, "server_tool_use", None) if uso is not None else None
    solicitudes_reportadas = (
        getattr(uso_herramientas_servidor, "web_search_requests", None)
        if uso_herramientas_servidor is not None
        else None
    )

    exitosas = 0
    con_error = 0
    codigos_error: list[str] = []
    for bloque in getattr(respuesta, "content", None) or []:
        if getattr(bloque, "type", None) != "web_search_tool_result":
            continue
        contenido = bloque.content
        codigo_error = getattr(contenido, "error_code", None)
        if codigo_error:
            con_error += 1
            codigos_error.append(codigo_error)
        else:
            exitosas += 1

    return UsoBusquedaWeb(
        solicitudes_reportadas=solicitudes_reportadas,
        busquedas_exitosas=exitosas,
        busquedas_con_error=con_error,
        codigos_error=codigos_error,
    )


def _codigo_http(excepcion: Exception) -> str | None:
    """Devuelve el status_code de una excepción del SDK como texto,
    cuando la excepción lo expone (AuthenticationError, RateLimitError,
    APIStatusError). Las excepciones puramente de transporte
    (APITimeoutError, APIConnectionError) no tienen status_code — en
    ese caso devuelve None en vez de inventar un código."""
    status_code = getattr(excepcion, "status_code", None)
    return str(status_code) if status_code is not None else None


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
        # max_retries=0: el Paso 5A controla el costo de la primera
        # validación real limitándola a una única solicitud lógica, sin
        # los reintentos automáticos que el SDK aplica por defecto.
        return anthropic.Anthropic(api_key=api_key, max_retries=0)

    def _construir_prompt(self, contexto: ContextoEntidad) -> str:
        try:
            prompt_base = cargar_prompt(NOMBRE_PROMPT_INVESTIGACION)
        except PromptNoEncontradoError as exc:
            raise ErrorProveedorAnthropic(str(exc)) from exc
        return f"{prompt_base}\n\nNombre del POI: {contexto.nombre}{_INSTRUCCION_FORMATO_RESPUESTA}"

    def _construir_metricas(
        self,
        *,
        id_intento: str,
        iniciado_en: str,
        inicio_monotonico: float,
        resultado: str,
        llamadas: int,
        fase_error: str | None = None,
        codigo_error: str | None = None,
        mensaje_error: str | None = None,
        tokens: UsoTokens | None = None,
        busqueda_web: UsoBusquedaWeb | None = None,
        modelo_reportado: str | None = None,
        stop_reason: str | None = None,
    ) -> MetricasInvestigacion:
        finalizado_en = datetime.now().isoformat(timespec="seconds")
        duracion_ms = int((time.monotonic() - inicio_monotonico) * 1000)
        modelo_para_costo = modelo_reportado or self.modelo

        if fase_error == FASE_ANTES_DE_LLAMAR:
            # Ninguna llamada llegó a hacerse: el costo es exactamente
            # cero para los cinco componentes, no un dato faltante — no
            # hay nada que estimar ni ninguna incertidumbre que marcar
            # como parcial.
            cero = Decimal("0")
            tokens_final = UsoTokens(entrada=0, salida=0, cache_escritura=0, cache_lectura=0)
            busqueda_web_final = UsoBusquedaWeb(
                solicitudes_reportadas=0, busquedas_exitosas=0, busquedas_con_error=0, codigos_error=[]
            )
            costos_final = CostosInvestigacion(
                tokens_entrada=cero,
                tokens_salida=cero,
                cache_escritura=cero,
                cache_lectura=cero,
                busqueda_web=cero,
                total_estimado=cero,
                costo_completo=True,
            )
            tarifa = None
        else:
            tokens_final = tokens if tokens is not None else UsoTokens()
            busqueda_web_final = busqueda_web if busqueda_web is not None else UsoBusquedaWeb()
            try:
                tarifa_configurada = costos.obtener_tarifa(modelo_para_costo)
            except costos.TarifaNoDisponibleError:
                tarifa_configurada = None
            if tarifa_configurada is None:
                costos_final = CostosInvestigacion()
                tarifa = None
            else:
                costos_final = costos.calcular_costos(tokens_final, busqueda_web_final, tarifa_configurada)
                tarifa = TarifaModelo(
                    moneda=tarifa_configurada.moneda,
                    modelo=tarifa_configurada.modelo,
                    vigente_desde=tarifa_configurada.vigente_desde,
                    fuente=tarifa_configurada.fuente,
                )

        return MetricasInvestigacion(
            id_intento=id_intento,
            iniciado_en=iniciado_en,
            finalizado_en=finalizado_en,
            duracion_ms=duracion_ms,
            proveedor=self.nombre,
            modelo=modelo_para_costo,
            resultado=resultado,
            fase_error=fase_error,
            codigo_error=codigo_error,
            mensaje_error=mensaje_error,
            llamadas_logicas_api=llamadas,
            reintentos_transporte=0,
            stop_reason=stop_reason,
            tokens=tokens_final,
            busqueda_web=busqueda_web_final,
            costos_usd=costos_final,
            tarifa=tarifa,
        )

    def investigar_entidad(self, contexto: ContextoEntidad) -> ResultadoInvestigacion:
        id_intento = uuid.uuid4().hex
        inicio_monotonico = time.monotonic()
        iniciado_en = datetime.now().isoformat(timespec="seconds")

        def _metricas(resultado: str, llamadas: int, **kwargs) -> MetricasInvestigacion:
            return self._construir_metricas(
                id_intento=id_intento,
                iniciado_en=iniciado_en,
                inicio_monotonico=inicio_monotonico,
                resultado=resultado,
                llamadas=llamadas,
                **kwargs,
            )

        try:
            cliente = self._crear_cliente()
            prompt = self._construir_prompt(contexto)
        except ErrorProveedorAnthropic as exc:
            exc.metricas = _metricas(
                RESULTADO_ERROR, 0, fase_error=FASE_ANTES_DE_LLAMAR, mensaje_error=str(exc)
            )
            raise

        try:
            respuesta = cliente.messages.create(
                model=self.modelo,
                max_tokens=MAX_TOKENS_RESPUESTA,
                thinking={"type": "disabled"},
                output_config={"format": {"type": "json_schema", "schema": ESQUEMA_RESPUESTA_ESTRUCTURADA}},
                messages=[{"role": "user", "content": prompt}],
                tools=[
                    {
                        "type": TIPO_HERRAMIENTA_BUSQUEDA_WEB,
                        "name": NOMBRE_HERRAMIENTA_BUSQUEDA_WEB,
                        "max_uses": MAX_USOS_BUSQUEDA_WEB,
                    }
                ],
            )
        except anthropic.AuthenticationError as exc:
            error = ErrorProveedorAnthropic("La API Key de Anthropic no es válida (error de autenticación).")
            error.metricas = _metricas(
                RESULTADO_ERROR, 1, fase_error=FASE_LLAMADA_HTTP,
                codigo_error=_codigo_http(exc), mensaje_error=str(error),
            )
            raise error from exc
        except anthropic.RateLimitError as exc:
            error = ErrorProveedorAnthropic(
                "Se alcanzó el límite de uso de la API de Anthropic. Intentá de nuevo más tarde."
            )
            error.metricas = _metricas(
                RESULTADO_ERROR, 1, fase_error=FASE_LLAMADA_HTTP,
                codigo_error=_codigo_http(exc), mensaje_error=str(error),
            )
            raise error from exc
        except anthropic.APITimeoutError as exc:
            error = ErrorProveedorAnthropic("La API de Anthropic no respondió a tiempo (timeout).")
            error.metricas = _metricas(
                RESULTADO_ERROR, 1, fase_error=FASE_LLAMADA_HTTP,
                codigo_error=_codigo_http(exc), mensaje_error=str(error),
            )
            raise error from exc
        except anthropic.APIConnectionError as exc:
            error = ErrorProveedorAnthropic(
                "No se pudo conectar con la API de Anthropic. Verificá la conexión a Internet."
            )
            error.metricas = _metricas(
                RESULTADO_ERROR, 1, fase_error=FASE_LLAMADA_HTTP,
                codigo_error=_codigo_http(exc), mensaje_error=str(error),
            )
            raise error from exc
        except anthropic.APIStatusError as exc:
            error = ErrorProveedorAnthropic(f"La API de Anthropic devolvió un error HTTP ({exc.status_code}).")
            error.metricas = _metricas(
                RESULTADO_ERROR, 1, fase_error=FASE_LLAMADA_HTTP,
                codigo_error=_codigo_http(exc), mensaje_error=str(error),
            )
            raise error from exc
        except anthropic.APIError as exc:
            error = ErrorProveedorAnthropic(f"Error inesperado de la API de Anthropic: {exc}")
            error.metricas = _metricas(
                RESULTADO_ERROR, 1, fase_error=FASE_LLAMADA_HTTP,
                codigo_error=_codigo_http(exc), mensaje_error=str(error),
            )
            raise error from exc

        # A partir de acá hubo una respuesta facturable de la API: se
        # recopila el uso ANTES de validar, para que quede disponible
        # incluso si la validación posterior falla (por ejemplo,
        # max_uses_exceeded, JSON inválido o estructura inválida).
        tokens = _extraer_uso_tokens(respuesta)
        busqueda_web = _extraer_uso_busqueda_web(respuesta)
        modelo_reportado = getattr(respuesta, "model", None) or self.modelo
        stop_reason = getattr(respuesta, "stop_reason", None)

        try:
            _validar_sin_errores_de_busqueda_web(respuesta)

            # Con la búsqueda web habilitada, Claude puede emitir más de
            # un bloque de texto (por ejemplo, una narración de "voy a
            # buscar esto" antes de invocar la herramienta, y recién
            # después la respuesta final). Solo el ÚLTIMO bloque de
            # texto es la respuesta al formato JSON pedido; concatenar
            # todos los bloques de texto rompería el JSON.
            bloques_de_texto = [
                bloque.text for bloque in respuesta.content if getattr(bloque, "type", None) == "text"
            ]
            texto_respuesta = bloques_de_texto[-1].strip() if bloques_de_texto else ""
            if not texto_respuesta:
                raise ErrorProveedorAnthropic(
                    "La API de Anthropic devolvió una respuesta vacía.", fase=FASE_RESPUESTA_VACIA
                )

            try:
                datos = json.loads(texto_respuesta)
            except json.JSONDecodeError as exc:
                raise ErrorProveedorAnthropic(
                    "La respuesta de la API de Anthropic no es un JSON válido.", fase=FASE_PARSEO_JSON
                ) from exc

            _validar_respuesta_estructurada(datos)
        except ErrorProveedorAnthropic as exc:
            exc.metricas = _metricas(
                RESULTADO_ERROR,
                1,
                fase_error=exc.fase or FASE_VALIDACION_ESTRUCTURA,
                codigo_error=exc.codigo,
                mensaje_error=str(exc),
                tokens=tokens,
                busqueda_web=busqueda_web,
                modelo_reportado=modelo_reportado,
                stop_reason=stop_reason,
            )
            raise

        resultado = self._resultado_desde_respuesta(datos)
        resultado.metricas = _metricas(
            RESULTADO_OK,
            1,
            tokens=tokens,
            busqueda_web=busqueda_web,
            modelo_reportado=modelo_reportado,
            stop_reason=stop_reason,
        )
        return resultado

    def _resultado_desde_respuesta(self, datos: dict) -> ResultadoInvestigacion:
        return ResultadoInvestigacion(
            borrador_master=datos["borrador_markdown"],
            fuentes=[_fuente_desde_diccionario(f) for f in datos["fuentes"]],
            contradicciones_detectadas=list(datos["contradicciones"]),
            observaciones=datos["observaciones"],
            nivel_confianza=datos["nivel_confianza"],
            metadatos_proveedor=MetadatosProveedor(nombre=self.nombre, modelo=self.modelo),
        )
