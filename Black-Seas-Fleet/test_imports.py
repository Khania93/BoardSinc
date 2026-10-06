# scripts/test_imports.py
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from core.datos import DatosJuego
    print("Import core.datos -> OK")
    try:
        dj = DatosJuego()
        print("Instanciado DatosJuego correctamente (o no lanzó ImportError).")
    except Exception as e:
        print("DatosJuego instanciación falló (esperado si faltan dependencias):", e)
except Exception as e:
    print("Fallo importando core.datos:", repr(e))
