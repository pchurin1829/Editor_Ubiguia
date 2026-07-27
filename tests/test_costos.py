"""Pruebas del módulo de tarifas y cálculo de costos (costos.py).

No llaman a ninguna API real: son pruebas puramente aritméticas sobre
las tarifas configuradas y la función calcular_costos().

Ejecutar con:  python -m unittest discover -s tests -v
"""
import sys
import unittest
from decimal import Decimal
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from motor_investigacion import costos  # noqa: E402
from motor_investigacion.entidad import UsoBusquedaWeb, UsoTokens  # noqa: E402


class PruebasObtenerTarifa(unittest.TestCase):
    def test_obtiene_la_tarifa_configurada_para_claude_sonnet_5(self):
        tarifa = costos.obtener_tarifa("claude-sonnet-5")
        self.assertEqual(tarifa.modelo, "claude-sonnet-5")
        self.assertEqual(tarifa.moneda, "USD")
        self.assertIsInstance(tarifa.entrada_por_millon, Decimal)
        self.assertIsInstance(tarifa.salida_por_millon, Decimal)

    def test_modelo_sin_tarifa_configurada_lanza_error_claro(self):
        with self.assertRaises(costos.TarifaNoDisponibleError):
            costos.obtener_tarifa("modelo-que-no-existe")


class PruebasCalcularCostos(unittest.TestCase):
    def setUp(self):
        self.tarifa = costos.obtener_tarifa("claude-sonnet-5")

    def test_calcula_el_costo_completo_usando_decimal(self):
        tokens = UsoTokens(entrada=1_000_000, salida=1_000_000, cache_escritura=1_000_000, cache_lectura=1_000_000)
        busqueda_web = UsoBusquedaWeb(solicitudes_reportadas=2, busquedas_exitosas=2, busquedas_con_error=0, codigos_error=[])

        resultado = costos.calcular_costos(tokens, busqueda_web, self.tarifa)

        self.assertIsInstance(resultado.tokens_entrada, Decimal)
        self.assertEqual(resultado.tokens_entrada, Decimal("2.00"))
        self.assertEqual(resultado.tokens_salida, Decimal("10.00"))
        self.assertEqual(resultado.cache_escritura, Decimal("2.50"))
        self.assertEqual(resultado.cache_lectura, Decimal("0.20"))
        self.assertEqual(resultado.busqueda_web, Decimal("0.02"))
        self.assertEqual(resultado.total_estimado, Decimal("14.72"))
        self.assertTrue(resultado.costo_completo)

    def test_precision_decimal_no_es_aproximada_como_con_float(self):
        # 3 búsquedas a 0.01 USD cada una: con float, 0.01 * 3 puede
        # arrastrar error de representación binaria; con Decimal debe
        # dar exactamente 0.03.
        tokens = UsoTokens()
        busqueda_web = UsoBusquedaWeb(solicitudes_reportadas=3, busquedas_exitosas=3, busquedas_con_error=0, codigos_error=[])
        resultado = costos.calcular_costos(tokens, busqueda_web, self.tarifa)
        self.assertEqual(resultado.busqueda_web, Decimal("0.03"))

    def test_busqueda_con_error_no_se_considera_facturable(self):
        # 1 búsqueda exitosa + 1 con error: solo se cobra la exitosa,
        # según la documentación oficial ("If an error occurs during
        # web search, the web search will not be billed").
        tokens = UsoTokens()
        busqueda_web = UsoBusquedaWeb(
            solicitudes_reportadas=2, busquedas_exitosas=1, busquedas_con_error=1, codigos_error=["max_uses_exceeded"]
        )
        resultado = costos.calcular_costos(tokens, busqueda_web, self.tarifa)
        self.assertEqual(resultado.busqueda_web, Decimal("0.01"))

    def test_tokens_faltantes_dejan_ese_componente_en_none_y_total_parcial(self):
        tokens = UsoTokens(entrada=1_000_000, salida=None, cache_escritura=None, cache_lectura=None)
        busqueda_web = UsoBusquedaWeb(solicitudes_reportadas=None, busquedas_exitosas=None, busquedas_con_error=None, codigos_error=[])

        resultado = costos.calcular_costos(tokens, busqueda_web, self.tarifa)

        self.assertEqual(resultado.tokens_entrada, Decimal("2.00"))
        self.assertIsNone(resultado.tokens_salida)
        self.assertIsNone(resultado.cache_escritura)
        self.assertIsNone(resultado.cache_lectura)
        self.assertIsNone(resultado.busqueda_web)
        self.assertIsNone(resultado.total_estimado)
        self.assertFalse(resultado.costo_completo)

    def test_ningun_dato_disponible_produce_costos_completamente_nulos(self):
        resultado = costos.calcular_costos(UsoTokens(), UsoBusquedaWeb(), self.tarifa)
        self.assertIsNone(resultado.tokens_entrada)
        self.assertIsNone(resultado.tokens_salida)
        self.assertIsNone(resultado.cache_escritura)
        self.assertIsNone(resultado.cache_lectura)
        self.assertIsNone(resultado.busqueda_web)
        self.assertIsNone(resultado.total_estimado)
        self.assertFalse(resultado.costo_completo)

    def test_nunca_inventa_una_busqueda_facturable_a_partir_de_solicitudes_reportadas(self):
        # Aunque se reportaron 5 solicitudes, si no sabemos cuántas
        # fueron exitosas no se debe facturar nada por aproximación.
        tokens = UsoTokens()
        busqueda_web = UsoBusquedaWeb(solicitudes_reportadas=5, busquedas_exitosas=None, busquedas_con_error=None, codigos_error=[])
        resultado = costos.calcular_costos(tokens, busqueda_web, self.tarifa)
        self.assertIsNone(resultado.busqueda_web)
        self.assertFalse(resultado.costo_completo)


if __name__ == "__main__":
    unittest.main()
