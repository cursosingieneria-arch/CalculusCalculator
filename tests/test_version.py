"""Verifica la fuente única de versión (hallazgo B1: deriva de versión).

Antes core/settings.py y setup.py tenían el número hardcodeado por separado
(ambos "2.1.0") mientras el repo ya estaba en v2.1.2. Ahora ambos leen
core/_version.py; esta prueba bloquea que vuelvan a divergir.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OK = FAIL = 0
def check(d, c):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if c else (OK, FAIL + 1)
    if not c: print("FALLO:", d)

from core._version import __version__ as V
check("version con formato X.Y.Z", V.count(".") == 2)

# core/settings.py debe tomar APP_VERSION de la fuente única.
import core.settings as settings
check("settings.APP_VERSION == _version", settings.APP_VERSION == V)

# setup.py no debe hardcodear otra versión (debe importarla de core._version).
with open(os.path.join(ROOT, "setup.py"), encoding="utf-8") as f:
    setup_src = f.read()
check("setup.py importa core._version", "from core._version import" in setup_src)
check("setup.py no hardcodea APP_VERSION =", 'APP_VERSION = "' not in setup_src)

print("\nRESULTADO: %d OK, %d FALLO" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
