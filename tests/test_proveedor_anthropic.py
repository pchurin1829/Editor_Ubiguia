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
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import httpx  # noqa: E402

import anthropic  # noqa: E402
from motor_investigacion import proveedor_activo  # noqa: E402
from motor_investigacion import proveedor_anthropic  # noqa: E402
from motor_investigacion.entidad import ContextoEntidad, FuenteInvestigacion, MetadatosProveedor  # noqa: E402
from motor_investigacion.proveedor import ProveedorInvestigacion  # noqa: E402
from motor_investigacion.proveedor_anthropic import (  # noqa: E402
    DEFAULT_MODEL,
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
            [{"type": "web_search_20250305", "name": "web_search", "max_uses": 1}],
        )

    def test_la_busqueda_web_queda_limitada_a_un_solo_uso_en_el_paso_5a(self):
        # Control de costo previo a la primera validación real: como
        # mucho una búsqueda web por llamada.
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_estructurada_valida()
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        self.assertEqual(kwargs["tools"][0]["max_uses"], 1)

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


if __name__ == "__main__":
    unittest.main()
