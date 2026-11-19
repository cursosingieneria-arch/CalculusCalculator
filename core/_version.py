"""Fuente única de la versión de la aplicación.

Sin imports (no depende de Qt), para poder usarse tanto desde el código de la
app (core/settings.py) como desde el empaquetado (setup.py) sin inconsistencias.
Mantener sincronizado con la etiqueta de git y con update.md.
"""

__version__ = "2.1.2"
