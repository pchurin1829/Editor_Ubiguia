# Editor UBIGUIA MVP 1.0

## Instalación

Requiere Python 3.10 o superior, con Tk incluido (la instalación estándar de python.org para Windows ya lo incluye; no se instala con pip).

Instalar las dependencias del proyecto:

```
pip install -r requirements.txt
```

Para usar el proveedor real de Anthropic en el Motor de Investigación, configurar la variable de entorno `ANTHROPIC_API_KEY`. Sin ella, el Motor sigue funcionando con el proveedor simulado (`ProveedorInvestigacionSimulado`).

## Ejecutar

Ejecutar: `python src\main.py`

Generar EXE: doble clic en `build_exe.bat`. El script instala automáticamente su propia dependencia de empaquetado (`PyInstaller`); no requiere ningún paso manual adicional.
