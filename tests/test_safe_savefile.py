"""Pruebas de safe_sympify_savefile (headless)."""
import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sympy
from sympy import Symbol
from core.safe_parse import safe_sympify_savefile, UnsafeExpressionError

OK = FAIL = 0
def check(d, c):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if c else (OK, FAIL + 1)
    if not c: print("FALLO:", d)

# LaTeX ($) eval-free
check("latex frac", safe_sympify_savefile("$\\frac{1}{2}") == sympy.Rational(1, 2))
# expresion normal
check("expr", safe_sympify_savefile("x**2 + 1") == Symbol("x")**2 + 1)
# expansion de funcion f(x)
fs = {"f": ["f", "x**2", "Reals", "x"]}
check("f(3) -> 9", safe_sympify_savefile("f(3)", fs) == sympy.Integer(9))
check("f(x)+1", safe_sympify_savefile("f(x)+1", fs) == Symbol("x")**2 + 1)
# geometria round-trip
from sympy.geometry import Line, Point2D
obj = Line(Point2D(1, 2), Point2D(3, 4))
check("round-trip Line", safe_sympify_savefile(repr(obj)) == obj)
# inyeccion rechazada, sin efecto lateral
buf = io.StringIO()
rej = False
with contextlib.redirect_stdout(buf):
    try:
        safe_sympify_savefile("__import__('os').system('echo x')")
    except Exception:
        rej = True
check("rechaza __import__", rej)
check("sin efecto lateral", "x\n" not in buf.getvalue())
# fs malicioso: el cuerpo de la funcion tambien se valida
bad_fs = {"g": ["g", "__import__('os')", "Reals", "x"]}
rej2 = False
try:
    safe_sympify_savefile("g(1)", bad_fs)
except Exception:
    rej2 = True
check("fs malicioso rechazado", rej2)

print("\nRESULTADO: %d OK, %d FALLO" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
