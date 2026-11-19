"""Verifica que core.sympify quedó desacoplado de Qt (hallazgo B3).

Antes importaba QMessageBox a nivel de módulo, lo que impedía usar/probar el
núcleo sin entorno gráfico. Esta prueba lo importa y lo ejerce sin Qt instalado.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OK = FAIL = 0
def check(d, c):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if c else (OK, FAIL + 1)
    if not c: print("FALLO:", d)

# 1) Importar core.sympify no debe requerir PySide6/Qt.
import core.sympify as s
check("core.sympify importa sin Qt", True)
check("no quedó dependencia a QMessageBox", "QMessageBox" not in dir(s))

# 2) Funciona igual que antes para entradas válidas e inválidas.
check("2+2", s.sympify("2+2", {}) == 4)
check("x**2", str(s.sympify("x**2", {})) == "x**2")
check("entrada inválida devuelve texto", isinstance(s.sympify("import os", {}), str))

# 3) ui/i18n.py ya no existe (código muerto eliminado).
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
check("ui/i18n.py eliminado", not os.path.exists(os.path.join(root, "ui", "i18n.py")))

print("\nRESULTADO: %d OK, %d FALLO" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
