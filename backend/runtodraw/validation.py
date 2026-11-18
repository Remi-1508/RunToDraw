"""Validation des saisies utilisateur, indépendante de FastAPI (donc facile à tester)."""
import unicodedata

from runtodraw.glyphs import GLYPHS

SHAPES = ("square", "circle", "heart", "star", "infinity")
MAX_TEXT_LENGTH = 10


def normalize_text(raw: str) -> str:
    """Met le texte en majuscules sans accents et ne garde que les caractères dessinables (A-Z, 0-9, espace).

    Permissif : « é » devient « E », les autres caractères inconnus sont ignorés.
    Lève ValueError si le texte est trop long ou ne contient rien à dessiner.
    """
    decomposed = unicodedata.normalize("NFKD", raw or "")
    ascii_text = "".join(c for c in decomposed if not unicodedata.combining(c)).upper()
    text = " ".join("".join(c for c in ascii_text if c in GLYPHS or c == " ").split())
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Le texte est limité à {MAX_TEXT_LENGTH} caractères.")
    if not any(c in GLYPHS for c in text):
        raise ValueError("Le texte doit contenir au moins une lettre (A-Z) ou un chiffre (0-9).")
    return text
