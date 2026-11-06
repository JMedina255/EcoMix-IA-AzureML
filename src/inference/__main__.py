"""
Punto de entrada para ejecución como módulo: python -m src.inference
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
