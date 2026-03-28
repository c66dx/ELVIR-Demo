"""Configuración global de pytest: BD aislada para toda la suite."""
import os

# Debe aplicarse antes de que `app.database` cree el engine al importar `app.main`.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
