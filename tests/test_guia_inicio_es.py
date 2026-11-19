#!/usr/bin/env python3
"""Pruebas de regresion del asistente de inicio (ui/guide.py) en espanol.

Verifica que:
  1. _guide_text() devuelve el texto espanol cuando el idioma es es_ES, y que
     los caminos en/zh siguen funcionando.
  2. Todos los diccionarios bilingues tienen clave "es" (sin faltantes), de modo
     que el asistente nunca cae al chino con la app en espanol.
  3. Ningun texto espanol conserva caracteres chinos.
  4. Ya no se ofrece seleccion de idioma en el asistente (app solo en espanol):
     no quedan radios de idioma ni el callback _on_lang_pick.
  5. ui/guide.py compila.

ui/guide.py importa PySide6.QtWidgets/QtCore (no disponibles headless, sin
libEGL). Se instalan stubs minimos solo para importar el modulo y probar su
logica de texto; no se instancia ningun widget. sympy si esta instalado y se usa
tal cual.
"""
import os
import re
import sys
import types
import py_compile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r'[一-鿿]')


def _install_qt_stubs():
    class _Any:
        def __init__(self, *a, **k):
            pass
        def __getattr__(self, name):
            return _Any
        def __call__(self, *a, **k):
            return _Any()

    def _stub(name):
        if name in sys.modules:
            return
        m = types.ModuleType(name)
        m.__getattr__ = lambda attr: _Any  # type: ignore[attr-defined]
        sys.modules[name] = m

    for mod in ("PySide6", "PySide6.QtWidgets", "PySide6.QtCore", "PySide6.QtGui"):
        _stub(mod)


def _import_guide():
    _install_qt_stubs()
    sys.path.insert(0, ROOT)
    import ui.guide as g
    return g


def test_guide_text_prefiere_espanol():
    g = _import_guide()
    from core import settings
    d = {"zh": "ZH", "en": "EN", "es": "ES"}
    settings._current = "es_ES"
    assert g._guide_text(d) == "ES"
    settings._current = "en_US"
    assert g._guide_text(d) == "EN"
    settings._current = "zh_CN"
    assert g._guide_text(d) == "ZH"
    # Fallback: sin clave "es" cae al chino, no rompe.
    settings._current = "es_ES"
    assert g._guide_text({"zh": "ZH", "en": "EN"}) == "ZH"


def test_todos_los_dicts_tienen_espanol():
    g = _import_guide()
    faltan = []

    def check(d, path):
        if isinstance(d, dict) and "zh" in d:
            if "es" not in d:
                faltan.append(path)
            return
        if isinstance(d, dict):
            for k, v in d.items():
                check(v, f"{path}.{k}")
        elif isinstance(d, list):
            for i, v in enumerate(d):
                check(v, f"{path}[{i}]")

    check(g._GUIDE_STEPS, "_GUIDE_STEPS")
    check(g._GUIDE_EXERCISES, "_GUIDE_EXERCISES")
    check(g._SETTINGS_STEP_TITLE, "_SETTINGS_STEP_TITLE")
    check(g._SETUP_LABELS, "_SETUP_LABELS")
    assert not faltan, f"diccionarios sin traduccion al espanol: {faltan}"


def test_espanol_sin_chino():
    g = _import_guide()
    con_chino = []

    def check(d, path):
        if isinstance(d, dict):
            if "es" in d and isinstance(d["es"], str) and CJK.search(d["es"]):
                con_chino.append(path)
            for k, v in d.items():
                check(v, f"{path}.{k}")
        elif isinstance(d, list):
            for i, v in enumerate(d):
                check(v, f"{path}[{i}]")

    check(g._GUIDE_STEPS, "_GUIDE_STEPS")
    check(g._GUIDE_EXERCISES, "_GUIDE_EXERCISES")
    check(g._SETTINGS_STEP_TITLE, "_SETTINGS_STEP_TITLE")
    check(g._SETUP_LABELS, "_SETUP_LABELS")
    assert not con_chino, f"texto espanol con caracteres chinos: {con_chino}"


def test_sin_selector_de_idioma():
    """La app es solo en espanol: el asistente no debe ofrecer cambio de idioma."""
    src = open(os.path.join(ROOT, "ui", "guide.py"), encoding="utf-8").read()
    for simbolo in ("_on_lang_pick", "_lang_group", "QRadioButton(\"中文",
                    "QRadioButton(\"English", "QRadioButton(\"Español"):
        assert simbolo not in src, f"quedo rastro del selector de idioma: {simbolo!r}"


def test_guide_compila():
    py_compile.compile(os.path.join(ROOT, "ui", "guide.py"), doraise=True)


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
