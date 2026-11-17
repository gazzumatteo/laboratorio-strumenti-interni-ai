"""Per tutti i test: nessuna chiave di Gemini nell'ambiente.

Così un test non chiama mai l'API vera, nemmeno se chi lo lancia ha `GEMINI_API_KEY` impostata
nel proprio terminale. I test che vogliono una chiave la impostano da sé, e con un client finto.
"""

import pytest


@pytest.fixture(autouse=True)
def no_gemini_environment(monkeypatch):
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL"):
        monkeypatch.delenv(name, raising=False)
