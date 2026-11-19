#!/usr/bin/env python3
"""Pruebas de regresion para la localizacion de ayuda y mensajes al espanol.

Objetivo (prioridad del usuario: "que no se rompa el codigo, que no pegue con
nada"): verificar que
  1. ui.help._help_filename() selecciona help_es.html cuando el idioma es espanol,
     sin romper los caminos de ingles (en) ni del idioma base (chino).
  2. Existen los tres archivos de ayuda.
  3. help_es.html no conserva texto chino en el cuerpo (traduccion completa).
  4. Los mensajes QMessageBox de expr_viewer.py no conservan texto chino.
  5. Las cadenas chinas que el codigo usa como CLAVES DE DATOS / COMPARACIONES
     siguen intactas (no se tradujeron), que es lo que garantiza que la logica
     de geometria y del lienzo de expresiones sigue funcionando igual.
  6. Los archivos modificados compilan (py_compile).

El entorno de analisis no tiene libEGL/pantalla, por lo que PySide6.QtWidgets no
se puede importar de verdad. Se instalan stubs de PySide6 y de ui.ui_help solo
para poder importar ui.help y probar su logica pura de seleccion de archivo; no
se instancia ningun widget.
"""
import os
import re
import sys
import types
import py_compile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r'[一-鿿]')


# ----------------------------------------------------------------------------
# Stubs minimos de Qt y ui.ui_help para importar ui.help sin entorno grafico.
# ----------------------------------------------------------------------------
def _install_qt_stubs():
    class _Any:
        """Objeto/clase comodin: cualquier atributo o llamada devuelve otro _Any."""
        def __init__(self, *a, **k):
            pass
        def __getattr__(self, name):
            return _Any()
        def __call__(self, *a, **k):
            return _Any()

    def _stub_module(name):
        m = types.ModuleType(name)
        # Devolver la CLASE _Any (no una instancia) para que sirva como clase
        # base en "class Help(QWidget, Ui_help)" y tambien como callable.
        m.__getattr__ = lambda attr: _Any  # type: ignore[attr-defined]
        sys.modules[name] = m
        return m

    for mod in ("PySide6", "PySide6.QtWidgets", "PySide6.QtCore", "PySide6.QtGui"):
        if mod not in sys.modules:
            _stub_module(mod)

    # ui.ui_help: ui/help.py hace "from ui.ui_help import *"; basta con Ui_help.
    if "ui.ui_help" not in sys.modules:
        m = types.ModuleType("ui.ui_help")
        class Ui_help:  # noqa: N801
            def setupUi(self, *a, **k):
                pass
        m.Ui_help = Ui_help
        m.__all__ = ["Ui_help"]
        sys.modules["ui.ui_help"] = m


def test_help_filename_selecciona_espanol():
    _install_qt_stubs()
    sys.path.insert(0, ROOT)
    from core import settings
    import ui.help as help_mod

    casos = {
        "es_ES": "help_es.html",
        "es": "help_es.html",
        "en_US": "help_en.html",
        "en": "help_en.html",
        "zh_CN": "help.html",
        "": "help.html",
    }
    for lang, esperado in casos.items():
        settings._current = lang
        got = help_mod._help_filename()
        assert got == esperado, f"idioma {lang!r}: esperaba {esperado}, obtuve {got}"


def test_existen_los_tres_archivos_de_ayuda():
    for name in ("help.html", "help_en.html", "help_es.html"):
        assert os.path.isfile(os.path.join(ROOT, name)), f"falta {name}"


def test_help_es_sin_chino_en_cuerpo():
    txt = open(os.path.join(ROOT, "help_es.html"), encoding="utf-8").read()
    # La fuente CSS "Microsoft YaHei"/"SimSun" es latina; el cuerpo no debe tener CJK.
    assert not CJK.search(txt), "help_es.html conserva caracteres chinos"
    assert "<html lang=\"es\">" in txt
    # Identificadores de codigo que NO deben traducirse (se mantienen verbatim).
    for ident in ("FiniteSet", "Interval.Ropen", "sqrt(x)", "f(x).diff(x,n)",
                  "mathjax/es5/tex-svg.js"):
        assert ident in txt, f"help_es.html perdio el identificador {ident!r}"


def test_expr_viewer_qmessagebox_sin_chino():
    p = os.path.join(ROOT, "expr_calculator", "expr_viewer.py")
    lineas = open(p, encoding="utf-8").read().split("\n")
    restante = [(i + 1) for i, l in enumerate(lineas)
                if "QMessageBox" in l and CJK.search(l)]
    assert not restante, f"lineas QMessageBox con chino: {restante}"


def test_claves_de_datos_intactas():
    """Las cadenas chinas usadas como claves/comparaciones NO deben tocarse."""
    p = os.path.join(ROOT, "expr_calculator", "expr_viewer.py")
    txt = open(p, encoding="utf-8").read()
    claves = ["通过点", "参数关系", "斜率", "截距",
              "直线", "圆", "椭圆", "双曲线", "抛物线"]
    faltan = [k for k in claves if k not in txt]
    assert not faltan, f"se perdieron claves de datos (romperia la logica): {faltan}"


def test_archivos_modificados_compilan():
    for rel in ("expr_calculator/expr_viewer.py", "ui/help.py"):
        py_compile.compile(os.path.join(ROOT, rel), doraise=True)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    fallos = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            fallos += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - fallos}/{len(fns)} pruebas en verde")
    sys.exit(1 if fallos else 0)
