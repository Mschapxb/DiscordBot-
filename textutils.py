"""
textutils.py — Fonctions de texte PURES, sans état ni dépendance au reste du bot.

Extraites de bot.py pour alléger le monolithe : normalisation (accents/casse),
racinisation légère du français, similarité/dédoublonnage, découpe pour Discord,
et parsing JSON tolérant. Aucune de ces fonctions ne touche à la mémoire, au bot
Discord ou aux réglages — elles ne dépendent que de la bibliothèque standard, ce
qui les rend testables isolément et réutilisables partout.
"""
import re
import json
import unicodedata

# Seuil de similarité pour éviter les quasi-doublons (dédoublonnage strict).
DEDUP_SIMILARITY = 0.8

# Mots-outils français ignorés lors du découpage en mots significatifs.
_STOPWORDS_FR = {
    "avec", "cette", "cettes", "dans", "elle", "elles", "etre", "être", "fait", "faire",
    "mais", "meme", "même", "nous", "pour", "quand", "quel", "quelle", "quels", "quelles",
    "sans", "sont", "leur", "leurs", "tout", "toute", "tous", "toutes", "vous", "avoir",
    "plus", "moins", "tres", "très", "aussi", "comme", "alors", "donc", "ainsi", "chez",
    "entre", "sous", "cela", "ceci", "etait", "était", "avait", "peut", "veut", "bien",
    "encore", "juste", "vraiment", "parce",
}


def _fold(text):
    """Minuscules SANS accents, longueur PRÉSERVÉE caractère à caractère (é→e) : permet de
    retrouver la POSITION exacte d'un terme dans le texte d'origine (pour les extraits)."""
    out = []
    for ch in (text or "").lower():
        d = unicodedata.normalize("NFD", ch)
        base = next((c for c in d if unicodedata.category(c) != "Mn"), " ")
        out.append(base if base.isprintable() else " ")
    return "".join(out)


def _words(text):
    """Mots significatifs, insensibles aux ACCENTS et débarrassés des mots-outils : la même
    normalisation sert au dédoublonnage ET au tri par pertinence (mémoire, notes, recherche)."""
    toks = re.findall(r"[a-z0-9]{4,}", _fold(text))
    return {t for t in toks if t not in _STOPWORDS_FR}


# --- Racinisation légère (français très fléchi) -----------------------------
# Le rappel mémoire était purement lexical : « il JOUE à X » ne matchait pas
# « tu JOUAIS à quoi ? ». On ramène chaque mot à une racine grossière (accords,
# conjugaisons, dérivations courantes) pour que ces variantes se rejoignent.
# Zéro dépendance, rapide, ne sert QU'AU tri par pertinence (jamais à effacer/
# fusionner un souvenir) : une racine un peu trop large ne fait, au pire, que
# remonter un souvenir légèrement moins pertinent — aucun risque de correction.
_FR_SUFFIXES = sorted([
    "issaient", "eraient", "iraient", "assent", "issent", "eront", "iront",
    "erait", "irait", "aient", "ement", "ments", "ation", "ations", "atrice",
    "ateur", "ateurs", "ances", "ence", "ances", "erais", "erait", "ions",
    "iers", "ière", "ieres", "euses", "eux", "euse", "ique", "iques", "isme",
    "iste", "ist", "ance", "ente", "ents", "ance", "erai", "eras", "erez",
    "erons", "ront", "iez", "ais", "ait", "ant", "ent", "ons", "ez", "er",
    "ir", "re", "es", "ee", "ees", "aux", "als", "al", "le", "te", "ité",
    "ites", "age", "ages", "s", "x", "e",
], key=len, reverse=True)


def _stem(word):
    """Racine grossière : retire un suffixe flexionnel/dérivationnel courant tant
    qu'il reste ≥3 lettres. Assez pour rapprocher jouer/joue/jouais/jouait/jouaient
    (→ « jou »), stratégie/stratégique (→ « strateg »), sans écrouler des mots courts."""
    for suf in _FR_SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[:-len(suf)]
    return word


def _stems(text):
    """Ensemble des racines significatives d'un texte (pour le tri par pertinence tolérant)."""
    toks = re.findall(r"[a-z0-9]{3,}", _fold(text))
    return {_stem(t) for t in toks if t not in _STOPWORDS_FR and len(_stem(t)) >= 3}


def _normalize(text):
    return re.sub(r"\s+", " ", text.strip().lower())


def _too_similar(a, b, thresh=DEDUP_SIMILARITY):
    """Vrai si deux souvenirs disent en substance la même chose."""
    if _normalize(a) == _normalize(b):
        return True
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= thresh


def _similarity(a, b):
    """Ratio de similarité (0 à 1) entre deux textes, sur le chevauchement des mots.
    Sert à retrouver DE QUELLE note parle un signalement « c'est faux »."""
    if _normalize(a) == _normalize(b):
        return 1.0
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def smart_split(text, limit=2000):
    """Découpe un texte en morceaux ≤ limit, en respectant les sauts de ligne
    (une seule très longue ligne est coupée durement)."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            if current:
                chunks.append(current)
            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def _parse_json_loose(raw):
    """Parse du JSON même si le modèle l'entoure de texte ou de balises ```."""
    if not raw:
        return None
    s = re.sub(r"```(json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # repli : on isole le premier tableau ou objet complet
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = s.find(opener), s.rfind(closer)
        if 0 <= i < j:
            try:
                return json.loads(s[i:j + 1])
            except json.JSONDecodeError:
                continue
    return None
