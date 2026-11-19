"""Verifica la localización al español (P5), headless con QtCore.

- i18n/es_ES.ts tiene traducción española para todos los mensajes.
- i18n/es_ES.qm existe y QTranslator lo carga; una traducción conocida resuelve.
- core.settings fuerza es_ES como idioma único.
"""
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

OK = FAIL = 0
def check(d, c):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if c else (OK, FAIL + 1)
    if not c: print("FALLO:", d)

ts_path = os.path.join(ROOT, "i18n", "es_ES.ts")
qm_path = os.path.join(ROOT, "i18n", "es_ES.qm")

# 1) es_ES.ts: todos los mensajes con traducción no vacía ni "unfinished".
tree = ET.parse(ts_path)
root = tree.getroot()
check("idioma declarado es_ES", root.get("language") == "es_ES")
total = unfinished = 0
sample = None
for ctx in root.findall("context"):
    cname = ctx.findtext("name")
    for m in ctx.findall("message"):
        total += 1
        tr = m.find("translation")
        if tr is None or not (tr.text or "").strip() or tr.get("type") == "unfinished":
            unfinished += 1
        elif sample is None:
            sample = (cname, m.findtext("source"), tr.text)
check("hay ~288 mensajes", total >= 280)
check("ninguno sin terminar", unfinished == 0)

# 2) es_ES.qm existe y carga; la traducción de muestra resuelve.
check("es_ES.qm existe", os.path.exists(qm_path))
from PySide6.QtCore import QCoreApplication, QTranslator
app = QCoreApplication.instance() or QCoreApplication(sys.argv)
tr = QTranslator()
loaded = tr.load(qm_path)
check("QTranslator carga es_ES.qm", loaded)
app.installTranslator(tr)
if sample:
    ctx_name, src, expected = sample
    got = QCoreApplication.translate(ctx_name, src)
    check("traduce %r -> %r" % (src, expected), got == expected)

# 3) core.settings fuerza es_ES.
import core.settings as s
check("load_saved_language == es_ES", s.load_saved_language() == "es_ES")
s.apply_language("en_US")
check("apply_language ignora otros idiomas", s.current_language() == "es_ES")

print("\nRESULTADO: %d OK, %d FALLO (mensajes: %d, sin terminar: %d)" % (OK, FAIL, total, unfinished))
sys.exit(1 if FAIL else 0)
