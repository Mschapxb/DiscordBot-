"""Charge bot.py pour les tests, SANS toucher aux vraies données ni au réseau.

- le module est importé depuis un dossier temporaire : memory.json, history.json,
  forum_platform.db… y sont créés, jamais dans le dépôt ;
- le vrai .env n'est pas lu ;
- rien ne se connecte à Discord (bot.run n'est appelé que par bot.main()).

Lancement, depuis la racine du dépôt :

    python -m unittest discover tests
"""
import atexit
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

WORK = tempfile.mkdtemp(prefix="tenebris-tests-")
atexit.register(shutil.rmtree, WORK, ignore_errors=True)


def load_bot():
    """Le module bot, chargé une seule fois, dans le dossier de travail temporaire."""
    if "bot" not in sys.modules:
        import dotenv
        dotenv.load_dotenv = lambda *a, **k: False          # on ignore le vrai .env
        os.environ["FORUM_DB"] = os.path.join(WORK, "forum_platform.db")
        os.chdir(WORK)                                      # fichiers de données → dossier temporaire
        import bot  # noqa: F401
    return sys.modules["bot"]


class Typing:
    """Remplace `channel.typing()` (gestionnaire de contexte asynchrone)."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False
