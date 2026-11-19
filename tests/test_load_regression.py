"""Regresión end-to-end del camino de carga seguro, SIN Qt.

saves.py importa Qt (QFileDialog...), así que stubeamos los módulos Qt y
core.render para poder probar _load_expr_dict y la reconstrucción de geometría
de forma headless. El objetivo es demostrar que un archivo malicioso NO ejecuta
código y que un archivo válido reconstruye sus objetos.
"""
import os
import sys
import types
import io
import contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# --- stubs mínimos de Qt y render para importar functions.saves headless ---
def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

class _Dummy:  # objeto Qt genérico
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return _Dummy()
    def __call__(self, *a, **k): return _Dummy()

_stub("PySide6")
_stub("PySide6.QtWidgets", QFileDialog=_Dummy, QLineEdit=_Dummy, QMessageBox=_Dummy,
      QGraphicsView=_Dummy, QComboBox=_Dummy)
_stub("PySide6.QtCore", Qt=_Dummy())
_stub("core.render", setGraphicsView=lambda *a, **k: None, _svg_cache={})
_stub("ui", tabs_list=[], tabs_dict={})
_stub("core.settings", current_language=lambda: "zh_CN")

import functions.saves as saves

OK = FAIL = 0
def check(d, c):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if c else (OK, FAIL + 1)
    if not c: print("FALLO:", d)

# 1) Archivo válido: eqs/rels se reconstruyen
d = saves._load_expr_dict(["x**2-1", "y+2"], {})
check("eqs validas reconstruidas", len(d) == 2)

# 2) Archivo malicioso: la entrada se descarta y NO se ejecuta
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    d2 = saves._load_expr_dict(["__import__('os').system('echo HACKED')", "x+1"], {})
check("entrada maliciosa descartada", "__import__('os').system('echo HACKED')" not in d2)
check("entrada valida conservada", "x+1" in d2)
check("sin ejecucion (no 'HACKED' en stdout)", "HACKED" not in buf.getvalue())

# 3) Geometría: _fix_old_format reconstruye sin eval
from sympy.geometry import Line, Point2D
obj = Line(Point2D(0, 0), Point2D(1, 1))
rebuilt = saves._fix_old_format(None, "直线", repr(obj), {})
check("fix_old_format reconstruye Line", rebuilt == obj)

print("\nRESULTADO: %d OK, %d FALLO" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
