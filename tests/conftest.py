import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al sys.path para imports en pruebas
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
