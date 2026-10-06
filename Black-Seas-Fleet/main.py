# main.py
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

try:
    current_file = Path(__file__).resolve()
    project_root = current_file.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except Exception:
    logger.debug("No se pudo ajustar sys.path automáticamente")

def main():
    try:
        from ui.home import HomeApp
    except Exception:
        logger.exception("Error importando la aplicación. Comprueba la estructura de carpetas.")
        sys.exit(1)

    try:
        app = HomeApp()
        app.mainloop()
    except Exception:
        logger.exception("Error al iniciar la interfaz gráfica.")
        sys.exit(1)

if __name__ == "__main__":
    main()
