"""Pruebas de la Etapa 5 del Motor de Investigación de UBIGUIA:
ProveedorInvestigacionAnthropic y la selección de proveedor activo.

Ninguna prueba de este archivo llama a la API real de Anthropic: todas
las llamadas HTTP están mockeadas. No requieren ANTHROPIC_API_KEY real
ni conexión a Internet.

Ejecutar con:  python -m unittest discover -s tests -v
"""
import os
import sys
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
from motor_investigacion.entidad import ContextoEntidad  # noqa: E402
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

    def test_genera_borrador_y_fuentes_identificables_con_llamada_mockeada(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            instancia = ClienteFalso.return_value
            instancia.messages.create.return_value = _respuesta_falsa(
                "Hola, recibí el mensaje sobre POI de Prueba."
            )
            resultado = ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        instancia.messages.create.assert_called_once()
        self.assertIn("ProveedorInvestigacionAnthropic", resultado.borrador_master)
        self.assertIn("POI de Prueba", resultado.borrador_master)
        self.assertIn("Hola, recibí el mensaje", resultado.borrador_master)
        self.assertEqual(len(resultado.fuentes), 1)
        self.assertIn("Anthropic", resultado.fuentes[0].notas)
        self.assertEqual(resultado.contradicciones_detectadas, [])

    def test_no_consume_la_api_real_el_cliente_queda_mockeado(self):
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = _respuesta_falsa("ok")
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        ClienteFalso.assert_called_once_with(api_key="clave-de-prueba")

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
    """Etapa 6: el proveedor ya no tiene ningún prompt hardcodeado —
    debe cargarlo siempre desde disco vía cargar_prompt()."""

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
            ClienteFalso.return_value.messages.create.return_value = _respuesta_falsa("ok")
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        mock_cargar.assert_called_once_with("PROMPT_INVESTIGACION_v1.md")

    def test_el_contenido_cargado_llega_completo_al_proveedor(self):
        texto_prompt_de_prueba = "TEXTO_DE_PRUEBA_DEL_PROMPT_CARGADO_98765\ncon varias líneas\ny acentos: ó ñ"
        with (
            mock.patch(
                "motor_investigacion.proveedor_anthropic.cargar_prompt", return_value=texto_prompt_de_prueba
            ),
            mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso,
        ):
            ClienteFalso.return_value.messages.create.return_value = _respuesta_falsa("ok")
            ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())

        _args, kwargs = ClienteFalso.return_value.messages.create.call_args
        mensaje_enviado = kwargs["messages"][0]["content"]
        self.assertIn(texto_prompt_de_prueba, mensaje_enviado)

    def test_prompt_faltante_se_traduce_a_error_claro_del_proveedor(self):
        from motor_investigacion.prompts import PromptNoEncontradoError

        with mock.patch(
            "motor_investigacion.proveedor_anthropic.cargar_prompt",
            side_effect=PromptNoEncontradoError("no se encontró PROMPT_INVESTIGACION_v1.md"),
        ):
            with self.assertRaises(ErrorProveedorAnthropic) as ctx:
                ProveedorInvestigacionAnthropic().investigar_entidad(_contexto_de_prueba())
        self.assertNotIsInstance(ctx.exception, PromptNoEncontradoError)
        self.assertIn("PROMPT_INVESTIGACION_v1.md", str(ctx.exception))


class PruebasProveedorSimuladoSinCambios(unittest.TestCase):
    """El proveedor simulado no se tocó en la Etapa 6: sigue sin
    ninguna relación con el sistema de carga de prompts."""

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


if __name__ == "__main__":
    unittest.main()
