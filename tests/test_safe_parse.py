"""Pruebas del parser seguro (headless, sin Qt). Ejecutar con: python -m pytest o directo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sympy
from sympy import Symbol
from core.safe_parse import safe_sympify, UnsafeExpressionError

OK = 0
FAIL = 0


def check(desc, cond):
    global OK, FAIL
    if cond:
        OK += 1
    else:
        FAIL += 1
        print("FALLO:", desc)


# --- 1. Expresiones matemáticas válidas se reconstruyen correctamente ---
check("entero", safe_sympify("2+2") == 4)
check("potencia simbolica", safe_sympify("x**2") == Symbol("x") ** 2)
check("fraccion", safe_sympify("Rational(1, 2)") == sympy.Rational(1, 2))
check("trig+pi", safe_sympify("sin(pi/2)") == sympy.sin(sympy.pi / 2))
check("sqrt", safe_sympify("sqrt(2)") == sympy.sqrt(2))
check("expr compuesta", safe_sympify("x*y + 3*x - 1") == Symbol("x") * Symbol("y") + 3 * Symbol("x") - 1)
check("unario negativo", safe_sympify("-x") == -Symbol("x"))

# --- 2. Geometría (repr de objetos guardados) se reconstruye ---
from sympy.geometry import Point2D, Line, Circle
p = safe_sympify("Point2D(0, 0)")
check("Point2D", p == Point2D(0, 0))
ln = safe_sympify("Line(Point2D(0, 0), Point2D(1, 1))")
check("Line de dos puntos", ln == Line(Point2D(0, 0), Point2D(1, 1)))
c = safe_sympify("Circle(Point2D(0, 0), 5)")
check("Circle", c == Circle(Point2D(0, 0), 5))
# round-trip con repr real de sympy
obj = Line(Point2D(1, 2), Point2D(3, 4))
check("round-trip repr(Line)", safe_sympify(repr(obj)) == obj)

# --- 3. Inyección: debe rechazar, NO ejecutar ---
PAYLOADS = [
    "__import__('os')",
    "__import__('os').system('echo x')",
    "().__class__.__bases__",
    "x.__class__",
    "print('x')",
    "open('/etc/passwd')",
    "[c for c in ().__class__.__mro__]",
    "lambda: 1",
    "(1).__add__(2)",
    "globals()",
    "eval('1')",
]
for payload in PAYLOADS:
    rejected = False
    try:
        safe_sympify(payload)
    except (UnsafeExpressionError, SyntaxError):
        rejected = True
    except Exception as e:
        # cualquier otra excepción también es "no ejecutó el ataque", pero la marcamos
        rejected = True
        print("  (%s rechazado con %s)" % (payload, type(e).__name__))
    check("rechaza: %s" % payload, rejected)

# --- 4. Comparación directa con el comportamiento inseguro (demostración) ---
# El parser seguro NUNCA produce un efecto lateral. Verificamos que un payload con
# print() no imprime nada (si imprimiera, el ataque se habría ejecutado).
import io
import contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    try:
        safe_sympify("print('SIDE-EFFECT') or 0")
    except Exception:
        pass
check("sin efecto lateral (print no ejecutado)", "SIDE-EFFECT" not in buf.getvalue())

print("\nRESULTADO: %d OK, %d FALLO" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
