"""Pruebas del evaluador numérico seguro (headless, sin Qt)."""
import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.safe_eval import safe_eval, PY_ENGINE_NAMES, UnsafeExpressionError

OK = FAIL = 0
def check(d, c):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if c else (OK, FAIL + 1)
    if not c: print("FALLO:", d)

# --- 1. Aritmética válida (motor Python内置) ---
check("suma", safe_eval("2+2", PY_ENGINE_NAMES) == 4)
check("potencia", safe_eval("2**10", PY_ENGINE_NAMES) == 1024)
check("precedencia", safe_eval("2+3*4", PY_ENGINE_NAMES) == 14)
check("sqrt", abs(safe_eval("sqrt(2)", PY_ENGINE_NAMES) - 2**0.5) < 1e-12)
check("factorial", safe_eval("factorial(5)", PY_ENGINE_NAMES) == 120)
check("sin(pi) ~ 0", abs(safe_eval("sin(pi)", PY_ENGINE_NAMES)) < 1e-9)
check("división", safe_eval("7/2", PY_ENGINE_NAMES) == 3.5)
check("negativo", safe_eval("-5+2", PY_ENGINE_NAMES) == -3)

# --- 2. Inyección: debe rechazar, NO ejecutar ---
PAYLOADS = [
    "__import__('os').system('echo x')",
    "open('/etc/passwd')",
    "().__class__",
    "(1).__class__.__bases__",
    "eval('1+1')",
    "exec('x=1')",
    "globals()",
    "[].__class__.__mro__",
    "lambda: 1",
    "abs.__globals__",
]
for p in PAYLOADS:
    rej = False
    try:
        safe_eval(p, PY_ENGINE_NAMES)
    except Exception:
        rej = True
    check("rechaza: %s" % p, rej)

# --- 3. Sin efecto lateral ---
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    try:
        safe_eval("__import__('os').system('echo HACKED')", PY_ENGINE_NAMES)
    except Exception:
        pass
check("sin ejecucion", "HACKED" not in buf.getvalue())

# --- 4. Nombre no listado se rechaza (no NameError silencioso ni acceso global) ---
rej = False
try:
    safe_eval("sympify('x')", PY_ENGINE_NAMES)
except UnsafeExpressionError:
    rej = True
check("nombre no listado rechazado", rej)

print("\nRESULTADO: %d OK, %d FALLO" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
