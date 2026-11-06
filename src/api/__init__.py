"""
Paquete API REST de EcoMix IA (FastAPI).
Expone el motor de inferencia predictiva para integración con ASP.NET MVC 5.
"""

from .main import app, create_app
from .config import ApiSettings, get_settings

__all__ = ["app", "create_app", "ApiSettings", "get_settings"]
