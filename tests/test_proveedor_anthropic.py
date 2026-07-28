"""Pruebas de ProveedorInvestigacionAnthropic: conexión con la API,
selección de proveedor activo, uso del Prompt Maestro y (Paso 4) el
contrato de respuesta estructurada y validada.

Ninguna prueba de este archivo llama a la API real de Anthropic: todas
las llamadas HTTP están mockeadas. No requieren ANTHROPIC_API_KEY real
ni conexión a Internet.

Ejecutar con:  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import httpx  # noqa: E402

import anthropic  # noqa: E402
from motor_investigacion import costos  # noqa: E402
from motor_investigacion import proveedor_activo  # noqa: E402
from motor_investigacion import proveedor_anthropic  # noqa: E402
from motor_investigacion.entidad import (  # noqa: E402
    ContextoEntidad,
    FuenteInvestigacion,
    MetadatosProveedor,
    UsoTokens,
)
from motor_investigacion.proveedor import ProveedorInvestigacion  # noqa: E402
from motor_investigacion.proveedor_anthropic import (  # noqa: E402
    DEFAULT_MODEL,
    ESQUEMA_CONTRADICCION,
    ESQUEMA_FUENTE,
    ESQUEMA_RESPUESTA_ESTRUCTURADA,
    MAX_TOKENS_RESPUESTA,
    MAX_USOS_BUSQUEDA_WEB,
    ErrorProveedorAnthropic,
    ProveedorInvestigacionAnthropic,
)
from motor_investigacion.proveedor_simulado import ProveedorInvestigacionSimulado  # noqa: E402


def _contexto_de_prueba() -> ContextoEntidad:
    return ContextoEntidad(
        tipo_entidad="POI",
        id_entidad="poi-prueba-001",
        nombre="POI de Prueba",
        contexto_geografico={
            "ciudad": "CIUDAD DE PRUEBA",
            "provincia": "BUENOS AIRES",
            "pais": "ARGENTINA",
            "categoria": "Prueba",
        },
        ficha_actual="",
    )


def _respuesta_falsa(texto: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=texto)])


def _borrador_markdown_valido(nombre_poi: str = "POI de Prueba") -> str:
    """Borrador mínimo pero válido: incluye las 13 secciones numeradas
    obligatorias, sin redactar el contenido real del Prompt Maestro."""
    secciones = "\n\n".join(f"## {n}. Sección {n}\n\nContenido de prueba." for n in range(1, 14))
    return f"# {nombre_poi}\n\n{secciones}\n"


def _datos_respuesta_valida(**overrides) -> dict:
    datos = {
        "borrador_markdown": _borrador_markdown_valido(),
        "fuentes": [
            {
                "titulo": "Fuente de prueba",
                "url": "https://ejemplo.invalid/fuente",
                "sitio": "Sitio de prueba",
                "consultado_en": "2026-07-26T10:00:00",
                "secciones_respaldadas": ["2. Sección 2"],
                "confianza": "alta",
                "notas": "Nota de prueba.",
                "identificador": "src-01",
            }
        ],
        "contradicciones": [
            {"topic": "año de inauguración", "sources": ["src-01"], "detail": "Detalle de prueba."}
        ],
        "observaciones": "Observación de prueba para el editor.",
        "nivel_confianza": "MEDIO",
    }
    datos.update(overrides)
    return datos


def _respuesta_estructurada_valida(**overrides) -> SimpleNamespace:
    return _respuesta_falsa(json.dumps(_datos_respuesta_valida(**overrides)))


def _error_http(clase_excepcion, status_code: int, mensaje: str):
    """Construye una excepción real del SDK (misma jerarquía que usaría
    la API real) sin hacer ninguna llamada de red."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code, request=request, json={"error": {"message": mensaje}})
    return clase_excepcion(mensaje, response=response, body=None)


class PruebasProveedorAnthropic(unittest.TestCase):
    def setUp(self):
        self._entorno_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._entorno_previo)))

    def test_implementa_la_interfaz_de_proveedor_investigacion(self):
        proveedor = ProveedorInvestigacionAnthropic()
        self.assertIsInstance(proveedor, ProveedorInvestigacion)
        self.assertTrue(callable(proveedor.investigar_entidad))
        self.assertEqual(proveedor.nombre, "anthropic")
        self.assertEqual(proveedor.modelo, DEFAULT_MODEL)

        # Mismos métodos públicos que ProveedorInvestigacionSimulado, sin
        # agregar ninguno nuevo: el contrato de ProveedorInvestigacion no cambió.
        publicos_simulado = {
            nombre for nombre in vars(ProveedorInvestigacionSimulado) if not nombre.startswith("_")
        }
        publicos_anthropic = {
            nombre for nombre in vars(ProveedorInvestigacionAnthropic) if not nombre.startswith("_")
        }
        self.assertEqual(publicos_simulado, publicos_anthropic)

    def test_falla_claramente_sin_api_key(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        proveedor = ProveedorInvestigacionAnthropic()
        with self.assertRaises(ErrorProveedorAnthropic):
            proveedor.investigar_entidad(_contexto_de_prueba())

    def test_no_consume_la_api_real_el_cliente_queda_mockeado(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        ClienteFalso.assert_called_once_with(api_key="clave-de-prueba", max_retries=0)

    def test_el_cliente_se_crea_sin_reintentos_automaticos(self):
        # Paso 5A: la primera validación real queda limitada a una única
        # solicitud lógica, sin los reintentos automáticos que el SDK
        # aplica por defecto (max_retries=2).
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        _args, kwargs = ClienteFalso.call_args
        self.assertEqual(kwargs["max_retries"], 0)

    def test_usa_exactamente_el_modelo_claude_sonnet_5(self):
        self.assertEqual(DEFAULT_MODEL, "claude-sonnet-5")
        self.assertEqual(ProveedorInvestigacionAnthropic.modelo, "claude-sonnet-5")

        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        self.assertEqual(kwargs["model"], "claude-sonnet-5")

    def test_error_de_autenticacion_se_traduce_a_error_claro(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-invalida"
        excepcion = _error_http(anthropic.AuthenticationError, 401, "invalid x-api-key")
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertNotIsInstance(ctx.exception, anthropic.AuthenticationError)
        self.assertIn("autenticación", str(ctx.exception).lower())

    def test_limite_de_uso_se_traduce_a_error_claro(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        excepcion = _error_http(anthropic.RateLimitError, 429, "rate limited")
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertIn("límite de uso", str(ctx.exception).lower())

    def test_timeout_se_traduce_a_error_claro(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        excepcion = anthropic.APITimeoutError(request=request)
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertIn("timeout", str(ctx.exception).lower())

    def test_error_de_conexion_se_traduce_a_error_claro(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        excepcion = anthropic.APIConnectionError(request=request)
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertIn("conectar", str(ctx.exception).lower())

    def test_error_http_generico_se_traduce_a_error_claro(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        excepcion = _error_http(anthropic.InternalServerError, 500, "internal error")
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertIn("500", str(ctx.exception))

    def test_respuesta_vacia_se_traduce_a_error_claro(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_falsa("   ")
            with self.assertRaises(ErrorProveedorAnthropic):
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())


class PruebasCargaEnvLocal(unittest.TestCase):
    """Paso de configuración local: `.env.local` (raíz del proyecto,
    excluido de git) debe poder proveer ANTHROPIC_API_KEY sin depender
    de una variable de entorno global. Ninguna prueba de esta clase usa
    el `.env.local` real del proyecto (que sí puede tener una clave
    real): cada una apunta `_RUTA_ENV_LOCAL` a un archivo temporal."""

    def setUp(self):
        self._entorno_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._entorno_previo)))

    def _apuntar_env_local_a(self, ruta):
        return mock.patch("motor_investigacion.proveedor_anthropic._RUTA_ENV_LOCAL", ruta)

    def test_carga_la_clave_desde_env_local_cuando_no_esta_en_el_entorno(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with tempfile.TemporaryDirectory() as directorio_temporal:
            ruta_env_local = Path(directorio_temporal) / ".env.local"
            ruta_env_local.write_text("ANTHROPIC_API_KEY=clave-desde-env-local\n", encoding="utf-8")
            with self._apuntar_env_local_a(ruta_env_local):
                proveedor_anthropic._cargar_env_local()
        self.assertEqual(os.environ.get("ANTHROPIC_API_KEY"), "clave-desde-env-local")

    def test_la_variable_de_entorno_del_proceso_tiene_prioridad_sobre_env_local(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-del-entorno"
        with tempfile.TemporaryDirectory() as directorio_temporal:
            ruta_env_local = Path(directorio_temporal) / ".env.local"
            ruta_env_local.write_text("ANTHROPIC_API_KEY=clave-desde-env-local\n", encoding="utf-8")
            with self._apuntar_env_local_a(ruta_env_local):
                proveedor_anthropic._cargar_env_local()
        self.assertEqual(os.environ.get("ANTHROPIC_API_KEY"), "clave-del-entorno")

    def test_sin_clave_en_entorno_ni_en_env_local_mantiene_el_error_claro(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with tempfile.TemporaryDirectory() as directorio_temporal:
            ruta_env_local = Path(directorio_temporal) / ".env.local"  # no existe
            with self._apuntar_env_local_a(ruta_env_local):
                proveedor_anthropic._cargar_env_local()
                with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                    ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertIn("ANTHROPIC_API_KEY", str(ctx.exception))

    def test_env_local_inexistente_no_produce_ningun_error(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-del-entorno"
        with tempfile.TemporaryDirectory() as directorio_temporal:
            ruta_env_local = Path(directorio_temporal) / ".env.local"  # no existe
            with self._apuntar_env_local_a(ruta_env_local):
                proveedor_anthropic._cargar_env_local()  # no debe lanzar
        self.assertEqual(os.environ.get("ANTHROPIC_API_KEY"), "clave-del-entorno")

    def test_la_clave_nunca_aparece_en_el_mensaje_de_error(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-secreta-de-prueba-98765"
        excepcion = _error_http(anthropic.AuthenticationError, 401, "invalid x-api-key")
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertNotIn("clave-secreta-de-prueba-98765", str(ctx.exception))


class PruebasCrearProveedor(unittest.TestCase):
    def test_valor_por_defecto_de_la_constante_es_false(self):
        self.assertFalse(proveedor_activo.USAR_PROVEEDOR_REAL)

    def test_por_defecto_devuelve_el_proveedor_simulado(self):
        with mock.patch.object(proveedor_activo, "USAR_PROVEEDOR_REAL", False):
            proveedor = proveedor_activo.crear_proveedor()
        self.assertIsInstance(proveedor, ProveedorInvestigacionSimulado)

    def test_con_la_constante_en_true_devuelve_el_proveedor_anthropic(self):
        with mock.patch.object(proveedor_activo, "USAR_PROVEEDOR_REAL", True):
            proveedor = proveedor_activo.crear_proveedor()
        self.assertIsInstance(proveedor, ProveedorInvestigacionAnthropic)


class PruebasProveedorAnthropicUsaSistemaDePrompts(unittest.TestCase):
    """El proveedor no tiene ningún prompt hardcodeado — debe cargarlo
    siempre desde disco vía cargar_prompt()."""

    def setUp(self):
        self._entorno_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._entorno_previo)))
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"

    def test_proveedor_usa_el_archivo_de_prompt_correcto(self):
        with (
            mock.patch(
                "motor_investigacion.proveedor_anthropic.cargar_prompt", return_value="texto de prueba"
            ) as mock_cargar,
            mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso,
        ):
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        mock_cargar.assert_called_once_with("PROMPT_MAESTRO_INVESTIGACION_v1.0.md")

    def test_el_contenido_cargado_llega_completo_al_proveedor(self):
        texto_prompt_de_prueba = "TEXTO_DE_PRUEBA_DEL_PROMPT_CARGADO_98765\ncon varias líneas\ny acentos: ó ñ"
        with (
            mock.patch(
                "motor_investigacion.proveedor_anthropic.cargar_prompt", return_value=texto_prompt_de_prueba
            ),
            mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso,
        ):
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        mensaje_enviado = kwargs["messages"][0]["content"]
        self.assertIn(texto_prompt_de_prueba, mensaje_enviado)

    def test_carga_el_contenido_real_del_prompt_maestro_desde_disco(self):
        # A diferencia de la prueba anterior, acá no se mockea
        # cargar_prompt(): se lee el Prompt Maestro real desde
        # Docs/prompts/ y se verifica que llegue completo a la llamada
        # (mockeada) de Anthropic. Ninguna llamada de red ocurre.
        from motor_investigacion.prompts import cargar_prompt as cargar_prompt_real

        contenido_real = cargar_prompt_real("PROMPT_MAESTRO_INVESTIGACION_v1.0.md")

        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        mensaje_enviado = kwargs["messages"][0]["content"]
        self.assertIn(contenido_real, mensaje_enviado)

    def test_el_proveedor_no_contiene_un_prompt_hardcodeado(self):
        import inspect

        codigo_fuente = inspect.getsource(ProveedorInvestigacionAnthropic._construir_prompt)
        # El único origen de texto instructivo es cargar_prompt(); si
        # hubiera un prompt de respaldo escrito a mano, contendría
        # palabras propias del Prompt Maestro (por ejemplo "Investigador").
        self.assertIn("cargar_prompt", codigo_fuente)
        self.assertNotIn("Investigador", codigo_fuente)

    def test_prompt_faltante_se_traduce_a_error_claro_del_proveedor(self):
        from motor_investigacion.prompts import PromptNoEncontradoError

        with mock.patch(
            "motor_investigacion.proveedor_anthropic.cargar_prompt",
            side_effect=PromptNoEncontradoError("no se encontró PROMPT_MAESTRO_INVESTIGACION_v1.0.md"),
        ):
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertNotIsInstance(ctx.exception, PromptNoEncontradoError)
        self.assertIn("PROMPT_MAESTRO_INVESTIGACION_v1.0.md", str(ctx.exception))

    def test_prompt_faltante_nunca_llama_a_la_api(self):
        # Si el Prompt Maestro no se puede cargar, no debe existir ningún
        # camino alternativo que igual llame a la API con un prompt
        # interno de respaldo.
        from motor_investigacion.prompts import PromptNoEncontradoError

        with (
            mock.patch(
                "motor_investigacion.proveedor_anthropic.cargar_prompt",
                side_effect=PromptNoEncontradoError("no se encontró PROMPT_MAESTRO_INVESTIGACION_v1.0.md"),
            ),
            mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso,
        ):
            with self.assertRaises(ErrorProveedorAnthropic):
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        ClienteFalso.return_value.messages.create.assert_not_called()


class PruebasBusquedaWeb(unittest.TestCase):
    """Paso 5A: la herramienta oficial de búsqueda web del SDK
    (`web_search_20250305`) se agrega a la misma llamada de
    investigar_entidad(). Ninguna prueba de esta clase llama a la API
    real: el cliente de Anthropic queda mockeado, y las respuestas
    simuladas replican la forma documentada oficialmente por Anthropic
    para los bloques `server_tool_use` y `web_search_tool_result`."""

    def setUp(self):
        self._entorno_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._entorno_previo)))
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"

    def _bloque_server_tool_use(self):
        return SimpleNamespace(
            type="server_tool_use",
            id="srvtoolu_prueba_01",
            name="web_search",
            input={"query": "Casa Curutchet La Plata"},
        )

    def _bloque_busqueda_exitosa(
        self,
        url="https://es.wikipedia.org/wiki/Casa_Curutchet",
        titulo="Casa Curutchet - Wikipedia",
    ):
        resultado = SimpleNamespace(
            type="web_search_result",
            url=url,
            title=titulo,
            encrypted_content="contenido-cifrado-de-prueba",
            page_age="April 2026",
        )
        return SimpleNamespace(
            type="web_search_tool_result",
            tool_use_id="srvtoolu_prueba_01",
            content=[resultado],
        )

    def _bloque_busqueda_con_error(self, codigo="max_uses_exceeded"):
        error = SimpleNamespace(type="web_search_tool_result_error", error_code=codigo)
        return SimpleNamespace(
            type="web_search_tool_result",
            tool_use_id="srvtoolu_prueba_02",
            content=error,
        )

    def test_la_llamada_incluye_la_herramienta_oficial_de_busqueda_web(self):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        self.assertEqual(
            kwargs["tools"],
            [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        )

    def test_la_busqueda_web_queda_limitada_a_tres_usos(self):
        # Paso 5A.2: subido de 1 a 3 tras comprobar en la validación real
        # que una sola búsqueda agota el límite (max_uses_exceeded) antes
        # de completar la investigación.
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        self.assertEqual(kwargs["tools"][0]["max_uses"], 3)
        self.assertEqual(kwargs["tools"][0]["max_uses"], MAX_USOS_BUSQUEDA_WEB)

    def test_procesa_correctamente_una_respuesta_con_resultados_de_busqueda_real(self):
        datos = _datos_respuesta_valida()
        contenido = [
            SimpleNamespace(type="text", text="Voy a buscar información sobre este POI."),
            self._bloque_server_tool_use(),
            self._bloque_busqueda_exitosa(),
            SimpleNamespace(type="text", text=json.dumps(datos)),
        ]
        respuesta = SimpleNamespace(content=contenido)

        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = respuesta
            resultado = ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        # El contrato interno sigue siendo válido: el resultado final es
        # el mismo ResultadoInvestigacion de siempre, sin importar que
        # la respuesta haya incluido bloques intermedios de búsqueda
        # (server_tool_use / web_search_tool_result) antes del texto.
        self.assertEqual(resultado.borrador_master, datos["borrador_markdown"])
        self.assertEqual(len(resultado.fuentes), 1)
        self.assertIsInstance(resultado.fuentes[0], FuenteInvestigacion)
        self.assertEqual(resultado.metadatos_proveedor, MetadatosProveedor(nombre="anthropic", modelo=DEFAULT_MODEL))

    def test_busqueda_con_error_produce_error_claro(self):
        contenido = [
            self._bloque_server_tool_use(),
            self._bloque_busqueda_con_error("max_uses_exceeded"),
            SimpleNamespace(type="text", text=json.dumps(_datos_respuesta_valida())),
        ]
        respuesta = SimpleNamespace(content=contenido)

        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = respuesta
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertIn("max_uses_exceeded", str(ctx.exception))

    def test_busqueda_sin_resultados_no_es_tratada_como_error(self):
        # Según la documentación oficial: una búsqueda que no encuentra
        # nada devuelve una lista de contenido vacía, no un error. Eso
        # no debe bloquear el resto del procesamiento.
        bloque_sin_resultados = SimpleNamespace(
            type="web_search_tool_result", tool_use_id="srvtoolu_prueba_03", content=[]
        )
        datos = _datos_respuesta_valida()
        contenido = [bloque_sin_resultados, SimpleNamespace(type="text", text=json.dumps(datos))]
        respuesta = SimpleNamespace(content=contenido)

        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = respuesta
            resultado = ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertEqual(resultado.borrador_master, datos["borrador_markdown"])

    def test_ninguna_llamada_alcanza_la_red_real(self):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        # anthropic.Anthropic queda completamente reemplazado por el
        # mock: ninguna llamada real puede haber ocurrido.
        ClienteFalso.assert_called_once()


class PruebasRespuestaEstructurada(unittest.TestCase):
    """Paso 4: el proveedor pide una respuesta JSON estructurada y
    validable, y la transforma en un ResultadoInvestigacion completo.
    Ninguna prueba de esta clase llama a la API real: la respuesta
    'mockeada' simula la forma que tendría una respuesta real."""

    def setUp(self):
        self._entorno_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._entorno_previo)))
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"

    def _investigar_con_respuesta(self, respuesta):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = respuesta
            return ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

    # 1 y 2: respuesta estructurada válida -> resultado correcto; el
    # borrador completo llega intacto (sin envolverlo en ninguna plantilla).
    def test_respuesta_valida_produce_resultado_con_el_borrador_completo(self):
        datos = _datos_respuesta_valida()
        resultado = self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertEqual(resultado.borrador_master, datos["borrador_markdown"])

    # 3: las fuentes se conservan estructuradas.
    def test_las_fuentes_se_conservan_estructuradas(self):
        resultado = self._investigar_con_respuesta(_respuesta_estructurada_valida())
        self.assertEqual(len(resultado.fuentes), 1)
        fuente = resultado.fuentes[0]
        self.assertIsInstance(fuente, FuenteInvestigacion)
        self.assertEqual(fuente.titulo, "Fuente de prueba")
        self.assertEqual(fuente.url, "https://ejemplo.invalid/fuente")
        self.assertEqual(fuente.sitio, "Sitio de prueba")
        self.assertEqual(fuente.consultado_en, "2026-07-26T10:00:00")
        self.assertEqual(fuente.secciones_respaldadas, ["2. Sección 2"])
        self.assertEqual(fuente.confianza, "alta")
        self.assertEqual(fuente.notas, "Nota de prueba.")
        self.assertEqual(fuente.identificador, "src-01")

    # 4: las contradicciones se conservan.
    def test_las_contradicciones_se_conservan(self):
        datos = _datos_respuesta_valida()
        resultado = self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertEqual(resultado.contradicciones_detectadas, datos["contradicciones"])

    # 5: las observaciones se conservan.
    def test_las_observaciones_se_conservan(self):
        datos = _datos_respuesta_valida(observaciones="Observación específica de esta prueba.")
        resultado = self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertEqual(resultado.observaciones, "Observación específica de esta prueba.")

    # 6: el nivel de confianza se valida (caso válido) y se conserva,
    # junto con los metadatos del proveedor y del modelo.
    def test_nivel_de_confianza_valido_se_conserva_junto_a_metadatos(self):
        for nivel in ("ALTO", "MEDIO", "BAJO"):
            with self.subTest(nivel=nivel):
                datos = _datos_respuesta_valida(nivel_confianza=nivel)
                resultado = self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
                self.assertEqual(resultado.nivel_confianza, nivel)
                self.assertEqual(resultado.metadatos_proveedor, MetadatosProveedor(nombre="anthropic", modelo=DEFAULT_MODEL))

    def test_nivel_de_confianza_invalido_produce_error_claro(self):
        datos = _datos_respuesta_valida(nivel_confianza="MUY_ALTO")
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertIn("nivel_confianza", str(ctx.exception))

    # 7: falta de campo obligatorio -> error claro.
    def test_falta_de_campo_obligatorio_produce_error_claro(self):
        for campo in ("borrador_markdown", "fuentes", "contradicciones", "observaciones", "nivel_confianza"):
            with self.subTest(campo=campo):
                datos = _datos_respuesta_valida()
                del datos[campo]
                with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                    self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
                self.assertIn(campo, str(ctx.exception))

    def test_borrador_vacio_produce_error_claro(self):
        datos = _datos_respuesta_valida(borrador_markdown="   ")
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertIn("borrador_markdown", str(ctx.exception))

    def test_borrador_sin_secciones_obligatorias_produce_error_claro(self):
        datos = _datos_respuesta_valida(borrador_markdown="# POI de Prueba\n\nTexto sin secciones numeradas.")
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertIn("secciones", str(ctx.exception).lower())

    # 8: tipo de dato incorrecto -> error claro.
    def test_fuentes_con_tipo_incorrecto_produce_error_claro(self):
        datos = _datos_respuesta_valida(fuentes="no es una lista")
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertIn("fuentes", str(ctx.exception))

    def test_elemento_de_fuentes_con_tipo_incorrecto_produce_error_claro(self):
        datos = _datos_respuesta_valida(fuentes=["esto debería ser un objeto"])
        with self.assertRaises(ErrorProveedorAnthropic):
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))

    def test_secciones_respaldadas_con_tipo_incorrecto_produce_error_claro(self):
        datos = _datos_respuesta_valida()
        datos["fuentes"][0]["secciones_respaldadas"] = "2. Sección 2"
        with self.assertRaises(ErrorProveedorAnthropic):
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))

    def test_contradicciones_con_tipo_incorrecto_produce_error_claro(self):
        datos = _datos_respuesta_valida(contradicciones="no es una lista")
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertIn("contradicciones", str(ctx.exception))

    def test_observaciones_con_tipo_incorrecto_produce_error_claro(self):
        datos = _datos_respuesta_valida(observaciones=["no es texto"])
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
        self.assertIn("observaciones", str(ctx.exception))

    # 9: JSON inválido o respuesta vacía -> error claro.
    def test_json_invalido_produce_error_claro(self):
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(_respuesta_falsa("esto no es JSON válido {{{"))
        self.assertIn("JSON", str(ctx.exception))

    def test_json_valido_pero_no_es_un_objeto_produce_error_claro(self):
        with self.assertRaises(ErrorProveedorAnthropic):
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(["esto", "es", "una", "lista"])))

    def test_respuesta_vacia_no_llega_a_intentar_parsear_json(self):
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(_respuesta_falsa("   "))
        self.assertIn("vacía", str(ctx.exception).lower())

    # 10: el proveedor no escribe archivos.
    def test_el_modulo_no_escribe_archivos(self):
        import inspect

        import motor_investigacion.proveedor_anthropic as modulo_anthropic

        codigo_fuente = inspect.getsource(modulo_anthropic)
        for señal_de_escritura in ("write_text(", "open(", "escribir_archivo_atomico"):
            self.assertNotIn(señal_de_escritura, codigo_fuente)

    def test_respuesta_invalida_no_devuelve_resultado_parcial(self):
        # Si la validación falla, no debe existir ningún resultado
        # parcialmente construido: la excepción es la única salida.
        datos = _datos_respuesta_valida(nivel_confianza="INVALIDO")
        try:
            self._investigar_con_respuesta(_respuesta_falsa(json.dumps(datos)))
            self.fail("Se esperaba ErrorProveedorAnthropic")
        except ErrorProveedorAnthropic:
            pass


class PruebasProveedorSimuladoSinCambios(unittest.TestCase):
    """El proveedor simulado no usa el sistema de prompts ni la API, y
    sigue cumpliendo el mismo contrato genérico (incluyendo los campos
    agregados en el Paso 4), de forma determinista y sin red."""

    def test_proveedor_simulado_no_usa_el_sistema_de_prompts(self):
        import inspect

        import motor_investigacion.proveedor_simulado as modulo_simulado

        codigo_fuente = inspect.getsource(modulo_simulado)
        self.assertNotIn("cargar_prompt", codigo_fuente)
        self.assertNotIn("motor_investigacion.prompts", codigo_fuente)

    def test_proveedor_simulado_sigue_funcionando_igual(self):
        resultado = ProveedorInvestigacionSimulado().investigar_entidad(_contexto_de_prueba())
        self.assertIn("POI de Prueba", resultado.borrador_master)
        self.assertEqual(len(resultado.fuentes), 1)
        self.assertEqual(resultado.contradicciones_detectadas, [])
        self.assertIn(resultado.nivel_confianza, ("ALTO", "MEDIO", "BAJO"))
        self.assertTrue(resultado.observaciones)
        self.assertEqual(resultado.metadatos_proveedor, MetadatosProveedor(nombre="simulado", modelo="mock-1"))


def _uso_de_prueba(entrada=100, salida=200, cache_escritura=0, cache_lectura=0, solicitudes_busqueda=1):
    server_tool_use = SimpleNamespace(web_search_requests=solicitudes_busqueda, web_fetch_requests=0)
    return SimpleNamespace(
        input_tokens=entrada,
        output_tokens=salida,
        cache_creation_input_tokens=cache_escritura,
        cache_read_input_tokens=cache_lectura,
        server_tool_use=server_tool_use,
    )


def _bloque_busqueda_exitosa(tool_use_id="srvtoolu_01"):
    resultado = SimpleNamespace(
        type="web_search_result",
        url="https://es.wikipedia.org/wiki/Casa_Curutchet",
        title="Casa Curutchet - Wikipedia",
        encrypted_content="contenido-cifrado-de-prueba",
        page_age="April 2026",
    )
    return SimpleNamespace(type="web_search_tool_result", tool_use_id=tool_use_id, content=[resultado])


def _bloque_busqueda_con_error(codigo="max_uses_exceeded", tool_use_id="srvtoolu_02"):
    error = SimpleNamespace(type="web_search_tool_result_error", error_code=codigo)
    return SimpleNamespace(type="web_search_tool_result", tool_use_id=tool_use_id, content=error)


def _respuesta_exitosa_con_uso(usage=None, bloques_busqueda=(), stop_reason="end_turn", modelo="claude-sonnet-5"):
    datos = _datos_respuesta_valida()
    contenido = list(bloques_busqueda) + [SimpleNamespace(type="text", text=json.dumps(datos))]
    return SimpleNamespace(content=contenido, usage=usage or _uso_de_prueba(), model=modelo, stop_reason=stop_reason)


class PruebasTelemetria(unittest.TestCase):
    """Telemetría y costos: cada intento (exitoso o fallido) recopila una
    MetricasInvestigacion. Ninguna prueba de esta clase llama a la API
    real de Anthropic ni consulta saldo."""

    def setUp(self):
        self._entorno_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._entorno_previo)))
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"

    def _investigar_con_respuesta(self, respuesta):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = respuesta
            return ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

    # 1: investigación exitosa -> métricas completas.
    def test_metricas_completas_en_investigacion_exitosa(self):
        uso = _uso_de_prueba(entrada=1000, salida=500, cache_escritura=200, cache_lectura=300, solicitudes_busqueda=1)
        respuesta = _respuesta_exitosa_con_uso(usage=uso, bloques_busqueda=[_bloque_busqueda_exitosa()])

        resultado = self._investigar_con_respuesta(respuesta)

        metricas = resultado.metricas
        self.assertIsNotNone(metricas)
        self.assertEqual(metricas.resultado, "OK")
        self.assertEqual(metricas.proveedor, "anthropic")
        self.assertEqual(metricas.modelo, "claude-sonnet-5")
        self.assertEqual(metricas.llamadas_logicas_api, 1)
        self.assertEqual(metricas.reintentos_transporte, 0)
        self.assertIsNone(metricas.fase_error)
        self.assertIsNone(metricas.codigo_error)
        self.assertIsNone(metricas.mensaje_error)
        self.assertGreaterEqual(metricas.duracion_ms, 0)
        self.assertEqual(metricas.stop_reason, "end_turn")
        # Tokens de entrada y salida se conservan (prueba 4 de la lista).
        self.assertEqual(metricas.tokens.entrada, 1000)
        self.assertEqual(metricas.tokens.salida, 500)
        # Métricas de caché se conservan (prueba 5).
        self.assertEqual(metricas.tokens.cache_escritura, 200)
        self.assertEqual(metricas.tokens.cache_lectura, 300)
        # Búsquedas exitosas se cuentan (prueba 6).
        self.assertEqual(metricas.busqueda_web.busquedas_exitosas, 1)
        self.assertEqual(metricas.busqueda_web.busquedas_con_error, 0)
        self.assertEqual(metricas.busqueda_web.solicitudes_reportadas, 1)
        # Costo calculado correctamente con Decimal (prueba 11).
        self.assertIsInstance(metricas.costos_usd.total_estimado, Decimal)
        self.assertTrue(metricas.costos_usd.costo_completo)
        self.assertIsNotNone(metricas.tarifa)
        self.assertEqual(metricas.tarifa.modelo, "claude-sonnet-5")

    def test_busquedas_fallidas_no_se_facturan(self):
        # Unidad directa sobre el extractor de métricas: una respuesta
        # real nunca llega a esta mezcla (cualquier bloque de búsqueda
        # con error hace fallar toda la investigación, ver
        # test_max_uses_exceeded_conserva_metricas_disponibles), pero el
        # conteo de "cuántas búsquedas fueron exitosas vs. con error"
        # debe ser correcto de forma independiente a esa validación.
        respuesta = SimpleNamespace(
            content=[_bloque_busqueda_exitosa(), _bloque_busqueda_con_error("query_too_long")],
            usage=_uso_de_prueba(solicitudes_busqueda=2),
        )

        uso_busqueda = proveedor_anthropic._extraer_uso_busqueda_web(respuesta)

        self.assertEqual(uso_busqueda.busquedas_exitosas, 1)
        self.assertEqual(uso_busqueda.busquedas_con_error, 1)
        self.assertEqual(uso_busqueda.codigos_error, ["query_too_long"])

        # Solo se cobra 1 búsqueda (la exitosa), no las 2 reportadas.
        tarifa = costos.obtener_tarifa("claude-sonnet-5")
        costo = costos.calcular_costos(UsoTokens(), uso_busqueda, tarifa)
        self.assertEqual(costo.busqueda_web, Decimal("0.01"))

    # 8: max_uses_exceeded conserva las métricas disponibles.
    def test_max_uses_exceeded_conserva_metricas_disponibles(self):
        uso = _uso_de_prueba(entrada=800, salida=50, solicitudes_busqueda=1)
        contenido = [_bloque_busqueda_con_error("max_uses_exceeded"), SimpleNamespace(type="text", text="{}")]
        respuesta = SimpleNamespace(content=contenido, usage=uso, model="claude-sonnet-5", stop_reason="tool_use")

        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(respuesta)

        metricas = ctx.exception.metricas
        self.assertIsNotNone(metricas)
        self.assertEqual(metricas.resultado, "ERROR")
        self.assertEqual(metricas.fase_error, "VALIDACION_BUSQUEDA_WEB")
        self.assertEqual(metricas.codigo_error, "max_uses_exceeded")
        self.assertEqual(metricas.llamadas_logicas_api, 1)
        # El uso ya reportado por la API se conserva pese al error.
        self.assertEqual(metricas.tokens.entrada, 800)
        self.assertEqual(metricas.tokens.salida, 50)
        self.assertEqual(metricas.busqueda_web.busquedas_con_error, 1)

    def test_otro_error_de_busqueda_web_conserva_metricas(self):
        uso = _uso_de_prueba()
        contenido = [_bloque_busqueda_con_error("query_too_long"), SimpleNamespace(type="text", text="{}")]
        respuesta = SimpleNamespace(content=contenido, usage=uso, model="claude-sonnet-5", stop_reason="tool_use")

        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(respuesta)

        metricas = ctx.exception.metricas
        self.assertEqual(metricas.fase_error, "VALIDACION_BUSQUEDA_WEB")
        self.assertEqual(metricas.codigo_error, "query_too_long")

    # 5: respuesta JSON inválida.
    def test_json_invalido_conserva_metricas(self):
        uso = _uso_de_prueba(entrada=10, salida=5)
        respuesta = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="esto no es JSON {{{")],
            usage=uso, model="claude-sonnet-5", stop_reason="end_turn",
        )
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(respuesta)
        metricas = ctx.exception.metricas
        self.assertEqual(metricas.fase_error, "PARSEO_JSON")
        self.assertEqual(metricas.tokens.entrada, 10)
        self.assertEqual(metricas.tokens.salida, 5)

    # 5 (bis): respuesta estructurada inválida (falta una clave obligatoria).
    def test_respuesta_estructurada_invalida_conserva_metricas(self):
        datos = _datos_respuesta_valida()
        del datos["nivel_confianza"]
        uso = _uso_de_prueba()
        respuesta = SimpleNamespace(
            content=[SimpleNamespace(type="text", text=json.dumps(datos))],
            usage=uso, model="claude-sonnet-5", stop_reason="end_turn",
        )
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(respuesta)
        metricas = ctx.exception.metricas
        self.assertEqual(metricas.fase_error, "VALIDACION_ESTRUCTURA")

    # 6: respuesta vacía.
    def test_respuesta_vacia_conserva_metricas(self):
        respuesta = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="   ")],
            usage=_uso_de_prueba(), model="claude-sonnet-5", stop_reason="end_turn",
        )
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            self._investigar_con_respuesta(respuesta)
        metricas = ctx.exception.metricas
        self.assertEqual(metricas.fase_error, "RESPUESTA_VACIA")
        self.assertEqual(metricas.resultado, "ERROR")

    # 7: error HTTP con información disponible (status_code presente).
    def test_error_http_con_codigo_disponible(self):
        excepcion = _error_http(anthropic.AuthenticationError, 401, "invalid x-api-key")
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        metricas = ctx.exception.metricas
        self.assertEqual(metricas.fase_error, "LLAMADA_HTTP")
        self.assertEqual(metricas.codigo_error, "401")
        self.assertEqual(metricas.llamadas_logicas_api, 1)
        self.assertIsNone(metricas.tokens.entrada)
        self.assertFalse(metricas.costos_usd.costo_completo)

    # 8: error HTTP sin ninguna información disponible (sin status_code).
    def test_error_http_sin_informacion_disponible(self):
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        excepcion = anthropic.APIConnectionError(request=request)
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        metricas = ctx.exception.metricas
        self.assertEqual(metricas.fase_error, "LLAMADA_HTTP")
        self.assertIsNone(metricas.codigo_error)
        self.assertEqual(metricas.llamadas_logicas_api, 1)

    # 9: error antes de llamar a la API (falta ANTHROPIC_API_KEY) -> 0 llamadas.
    def test_falta_api_key_registra_cero_llamadas_y_costo_cero(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with self.assertRaises(ErrorProveedorAnthropic) as ctx:
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        metricas = ctx.exception.metricas
        self.assertIsNotNone(metricas)
        self.assertEqual(metricas.fase_error, "ANTES_DE_LLAMAR")
        self.assertEqual(metricas.llamadas_logicas_api, 0)
        self.assertEqual(metricas.costos_usd.total_estimado, Decimal("0"))
        self.assertTrue(metricas.costos_usd.costo_completo)
        self.assertEqual(metricas.tokens.entrada, 0)

    # 9 (bis): error antes de llamar por Prompt Maestro faltante.
    def test_prompt_faltante_registra_cero_llamadas(self):
        from motor_investigacion.prompts import PromptNoEncontradoError

        with mock.patch(
            "motor_investigacion.proveedor_anthropic.cargar_prompt",
            side_effect=PromptNoEncontradoError("no se encontró el prompt"),
        ):
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        metricas = ctx.exception.metricas
        self.assertEqual(metricas.fase_error, "ANTES_DE_LLAMAR")
        self.assertEqual(metricas.llamadas_logicas_api, 0)

    def test_la_api_key_nunca_aparece_en_las_metricas(self):
        clave_secreta = "sk-ant-clave-secreta-de-prueba-98765"
        os.environ["ANTHROPIC_API_KEY"] = clave_secreta
        excepcion = _error_http(anthropic.AuthenticationError, 401, "invalid x-api-key")
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.side_effect = excepcion
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        metricas_json = json.dumps(ctx.exception.metricas.a_diccionario_json())
        self.assertNotIn(clave_secreta, metricas_json)

    def test_ninguna_prueba_de_telemetria_alcanza_la_red_real(self):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_exitosa_con_uso()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        ClienteFalso.assert_called_once()


def _objetos_del_esquema(esquema):
    """Recorre recursivamente un JSON Schema (dict) y devuelve todos los
    sub-esquemas de tipo "object" que encuentra, incluyendo los anidados
    dentro de "properties" y "items". Usado para verificar que TODOS los
    objetos del esquema (no solo el de nivel superior) declaran
    additionalProperties=False y required completo."""
    objetos = []
    if not isinstance(esquema, dict):
        return objetos
    if esquema.get("type") == "object":
        objetos.append(esquema)
    for propiedad in esquema.get("properties", {}).values():
        objetos.extend(_objetos_del_esquema(propiedad))
    if "items" in esquema:
        objetos.extend(_objetos_del_esquema(esquema["items"]))
    return objetos


class PruebasStructuredOutputs(unittest.TestCase):
    """Corrección del fallo real del intento 5 (stop_reason=end_turn pero
    JSON inválido): en vez de depender únicamente de instrucciones
    textuales para "producir JSON válido", la llamada usa
    output_config.format (Structured Outputs de la API de Anthropic) con
    un esquema que representa exactamente el contrato que
    _resultado_desde_respuesta() espera. Ninguna prueba de esta clase
    llama a la API real: el cliente de Anthropic queda mockeado."""

    def setUp(self):
        self._entorno_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._entorno_previo)))
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"

    # 1: messages.create recibe output_config.format.
    def test_messages_create_recibe_output_config_format(self):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        self.assertIn("output_config", kwargs)
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(kwargs["output_config"]["format"]["schema"], ESQUEMA_RESPUESTA_ESTRUCTURADA)

    # 2: el esquema incluye todos los campos obligatorios del contrato
    # actual (los mismos que exige _validar_respuesta_estructurada()).
    def test_el_esquema_incluye_todos_los_campos_obligatorios(self):
        self.assertEqual(
            set(ESQUEMA_RESPUESTA_ESTRUCTURADA["required"]),
            {"borrador_markdown", "fuentes", "contradicciones", "observaciones", "nivel_confianza"},
        )
        self.assertEqual(
            set(ESQUEMA_FUENTE["required"]),
            {
                "titulo",
                "url",
                "sitio",
                "consultado_en",
                "secciones_respaldadas",
                "confianza",
                "notas",
                "identificador",
            },
        )
        self.assertEqual(set(ESQUEMA_CONTRADICCION["required"]), {"topic", "sources", "detail"})
        self.assertEqual(
            ESQUEMA_RESPUESTA_ESTRUCTURADA["properties"]["nivel_confianza"]["enum"], ["ALTO", "MEDIO", "BAJO"]
        )

    # 3: additionalProperties es false en TODOS los objetos del esquema
    # (nivel superior y los anidados en fuentes/contradicciones).
    def test_additionalProperties_false_en_todos_los_objetos_del_esquema(self):
        objetos = _objetos_del_esquema(ESQUEMA_RESPUESTA_ESTRUCTURADA)
        # Nivel superior + fuente + contradicción: al menos estos tres.
        self.assertGreaterEqual(len(objetos), 3)
        for objeto in objetos:
            with self.subTest(propiedades=list(objeto.get("properties", {}))):
                self.assertIs(objeto.get("additionalProperties"), False)
                self.assertEqual(set(objeto.get("required", [])), set(objeto.get("properties", {})))

    # 4: una respuesta válida se sigue convirtiendo correctamente en
    # ResultadoInvestigacion con output_config ya presente en la llamada.
    def test_respuesta_valida_se_convierte_en_resultado_investigacion(self):
        datos = _datos_respuesta_valida()
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_falsa(json.dumps(datos))
            resultado = ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertEqual(resultado.borrador_master, datos["borrador_markdown"])
        self.assertEqual(resultado.nivel_confianza, datos["nivel_confianza"])
        self.assertEqual(len(resultado.fuentes), 1)

    # 5: el Markdown extenso dentro de borrador_master conserva comillas,
    # saltos de línea y caracteres especiales al ir y volver por JSON.
    def test_borrador_markdown_conserva_caracteres_especiales(self):
        borrador_con_caracteres_especiales = (
            "# Casa Curutchet\n\n"
            + "\n\n".join(
                f'## {n}. Sección {n}\n\nTexto con "comillas", saltos\nde línea, barras \\ y acentos: ó ñ á.'
                for n in range(1, 14)
            )
        )
        datos = _datos_respuesta_valida(borrador_markdown=borrador_con_caracteres_especiales)
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_falsa(json.dumps(datos))
            resultado = ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertEqual(resultado.borrador_master, borrador_con_caracteres_especiales)
        self.assertIn('"comillas"', resultado.borrador_master)
        self.assertIn("\n", resultado.borrador_master)
        self.assertIn("\\", resultado.borrador_master)
        self.assertIn("ó ñ á", resultado.borrador_master)

    # 6: ya no se depende únicamente de la instrucción textual para
    # garantizar JSON válido — se retiró la orden redundante del prompt.
    def test_ya_no_depende_solo_de_la_instruccion_textual_para_json_valido(self):
        self.assertNotIn(
            "Respondé ÚNICAMENTE con un objeto JSON válido",
            proveedor_anthropic._INSTRUCCION_FORMATO_RESPUESTA,
        )
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        self.assertIn("output_config", kwargs)

    # 7: max_tokens sigue en 21000 (no se volvió a subir).
    def test_max_tokens_continua_en_21000(self):
        self.assertEqual(MAX_TOKENS_RESPUESTA, 21000)
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        self.assertEqual(kwargs["max_tokens"], 21000)

    # 8: max_uses sigue en 3 (cubierto también en PruebasBusquedaWeb;
    # se repite acá como parte del combo de invariantes de esta corrección).
    def test_max_uses_continua_en_3(self):
        self.assertEqual(MAX_USOS_BUSQUEDA_WEB, 3)

    # 9: max_retries sigue en 0.
    def test_max_retries_continua_en_0(self):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        _args, kwargs = ClienteFalso.call_args
        self.assertEqual(kwargs["max_retries"], 0)

    # 10: solo existe una llamada lógica a messages.create.
    def test_solo_una_llamada_logica_a_messages_create(self):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        ClienteFalso.return_value.messages.create.assert_called_once()

    # 11: ninguna prueba de esta clase alcanza la red real.
    def test_ninguna_prueba_alcanza_la_red_real(self):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        ClienteFalso.assert_called_once()

    # 12: la telemetría sigue funcionando en éxito y en error, ahora con
    # output_config ya presente en la llamada (no se rompió nada del
    # mecanismo existente, ver también PruebasTelemetria).
    def test_telemetria_sigue_funcionando_en_exito_con_output_config(self):
        respuesta = _respuesta_exitosa_con_uso()
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = respuesta
            resultado = ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertEqual(resultado.metricas.resultado, "OK")
        self.assertEqual(resultado.metricas.llamadas_logicas_api, 1)

    def test_telemetria_sigue_funcionando_en_error_con_output_config(self):
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_falsa("no es JSON {{{")
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertEqual(ctx.exception.metricas.resultado, "ERROR")
        self.assertEqual(ctx.exception.metricas.fase_error, "PARSEO_JSON")


if __name__ == "__main__":
    unittest.main()
