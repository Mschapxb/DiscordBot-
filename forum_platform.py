# -*- coding: utf-8 -*-
"""
FORUM PLATFORM — plateforme de forum interne pour Tenebris
===========================================================
Un vrai forum façon Forumactif, mais interne au bot : catégories, forums,
sous-forums, sujets, réponses, verrouillage/épinglage/archivage — le tout
posé sur SQLite (persistance garantie, WAL, index plein-texte FTS5) et
enrichi d'un GRAPHE DE CONNAISSANCES :

  • entités (personnages, lieux, événements, organisations, objets, mots-clés)
    extraites de chaque message (heuristique + LLM optionnel branché par le bot) ;
  • liens bidirectionnels entre sujets (manuels, wiki [[...]], ou détectés) ;
  • index consultable par thème, entité, relation ;
  • détection de doublons / sujets similaires ;
  • suggestions de sujets connexes.

Ce module est AUTONOME : aucune dépendance sur bot.py. Le bot lui injecte,
s'il le veut, une fonction d'extraction LLM (set_llm_extractor) et lit son API.
Toute l'API publique est synchrone et rapide (SQLite local) ; les rares
opérations lourdes (extraction LLM) sont asynchrones côté intégration.

Conventions :
  - niveaux de permission : 0 = lecture, 1 = écriture, 2 = modération ;
    un forum SANS règle est ouvert à tous (lecture + écriture).
  - syntaxe wiki dans les messages : [[Titre du sujet]] ou [[Titre|texte affiché]].
  - identifiants de sujets : slug façon forumactif « t42-mon-sujet ».
"""

import os
import re
import json
import sqlite3
import threading
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher

DB_FILE = os.getenv("FORUM_DB", "forum_platform.db")

# Types d'entités du graphe de connaissances (l'ordre sert à l'affichage).
ENTITY_TYPES = ("personnage", "lieu", "evenement", "organisation", "objet", "motcle")
ENTITY_LABELS = {
    "personnage": "Personnage", "lieu": "Lieu", "evenement": "Événement",
    "organisation": "Organisation", "objet": "Objet", "motcle": "Mot-clé",
}

# Seuils du moteur de similarité / doublons.
SIMILAR_TITLE_RATIO = 0.80     # titres quasi identiques → doublon probable
RELATED_MIN_SHARED = 2         # nb d'entités partagées pour suggérer un lien
AUTO_LINK_MIN_SHARED = 3       # nb d'entités partagées pour créer un lien auto
SUGGESTIONS_MAX = 8            # suggestions de sujets connexes affichées

# Mots vides français : filtrent l'extraction heuristique d'entités.
_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "d", "l", "et", "ou", "mais",
    "donc", "or", "ni", "car", "que", "qui", "quoi", "dont", "où", "ce", "cet",
    "cette", "ces", "son", "sa", "ses", "leur", "leurs", "mon", "ma", "mes", "ton",
    "ta", "tes", "notre", "votre", "nos", "vos", "il", "elle", "ils", "elles", "on",
    "nous", "vous", "je", "tu", "se", "ne", "pas", "plus", "moins", "très", "bien",
    "tout", "tous", "toute", "toutes", "être", "avoir", "faire", "dire", "aller",
    "pour", "par", "avec", "sans", "sous", "sur", "dans", "vers", "chez", "entre",
    "avant", "après", "pendant", "depuis", "jusque", "ainsi", "alors", "aussi",
    "comme", "quand", "si", "est", "sont", "était", "sera", "fut", "ont", "a",
    "au", "aux", "en", "y", "lui", "leur", "même", "autre", "autres", "chaque",
    "quelque", "quelques", "certains", "certaines", "cela", "ceci", "ça",
}


# ============================================================
# OUTILS TEXTE
# ============================================================
def _norm(s):
    """Normalise un texte pour comparaison : minuscules, sans accents ni ponctuation."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9\s-]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def _slugify(s, max_len=60):
    """Slug d'URL façon forumactif : « Le Prieuré d'Ambre » → le-prieure-d-ambre."""
    s = _norm(s).replace(" ", "-")
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:max_len] or "sujet"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _tokens(texte):
    """Jeu de mots significatifs (≥ 3 lettres, hors mots vides)."""
    return {w for w in _norm(texte).split() if len(w) >= 3 and w not in _STOPWORDS}


def _title_ratio(a, b):
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


# Syntaxe wiki : [[Titre]] ou [[Titre|texte affiché]]
WIKI_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]")


# ============================================================
# EXTRACTION HEURISTIQUE D'ENTITÉS (repli sans LLM)
# ============================================================
# Séquences de mots Capitalisés au milieu d'une phrase = noms propres probables.
_CAP_SEQ = re.compile(
    r"(?<![.!?»\"]\s)(?<!^)\b([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ][\wàâäéèêëîïôöùûüç'-]+"
    r"(?:\s+(?:de|du|des|d'|la|le|les|von|van)?\s*[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ][\wàâäéèêëîïôöùûüç'-]+){0,3})",
    re.MULTILINE)


def extract_entities_heuristic(texte):
    """Extraction SANS LLM : noms propres (séquences capitalisées hors début de
    phrase) classés « motcle » faute de mieux, + mots-clés fréquents.
    Le LLM, quand il est branché, fait bien mieux (types corrects) — ceci est
    le filet de sécurité pour que le graphe vive même sans quota API."""
    found = {}
    for m in _CAP_SEQ.finditer(texte or ""):
        nom = m.group(1).strip(" '-")
        if len(nom) < 3 or _norm(nom) in _STOPWORDS:
            continue
        found[_norm(nom)] = ("motcle", nom)
    # Mots significatifs répétés ≥ 3 fois → mots-clés thématiques.
    freq = {}
    for w in _norm(texte).split():
        if len(w) >= 5 and w not in _STOPWORDS:
            freq[w] = freq.get(w, 0) + 1
    for w, n in freq.items():
        if n >= 3 and w not in found:
            found[w] = ("motcle", w)
    return [{"type": t, "nom": nom} for t, nom in found.values()][:40]


# ============================================================
# LA PLATEFORME
# ============================================================
class ForumPlatform:
    """Toute l'API du forum interne. Une instance = une base SQLite.

    Usage minimal :
        forum = ForumPlatform()
        cid = forum.create_category("Chroniques")
        fid = forum.create_forum(cid, "Histoires d'Orbis")
        tid, warns = forum.create_topic(fid, "La Chute d'Ambre", "…texte…", 123, "mschap")
        forum.reply(tid, "Une réponse [[La Chute d'Ambre|liée]]", 456, "autre")
    """

    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_file, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._llm_extractor = None          # coroutine optionnelle branchée par le bot
        self._fts = self._init_schema()

    # ------------------------------------------------------------------
    # SCHÉMA
    # ------------------------------------------------------------------
    def _init_schema(self):
        c = self._conn
        with self._lock, c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS categories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                description TEXT DEFAULT '',
                position INTEGER DEFAULT 0,
                cree_le TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS forums(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                parent_id INTEGER REFERENCES forums(id) ON DELETE CASCADE,
                nom TEXT NOT NULL,
                description TEXT DEFAULT '',
                position INTEGER DEFAULT 0,
                cree_le TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS topics(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                forum_id INTEGER NOT NULL REFERENCES forums(id) ON DELETE CASCADE,
                titre TEXT NOT NULL,
                slug TEXT NOT NULL,
                auteur_id TEXT NOT NULL,
                auteur_nom TEXT NOT NULL,
                cree_le TEXT NOT NULL,
                maj_le TEXT NOT NULL,
                verrouille INTEGER DEFAULT 0,
                epingle INTEGER DEFAULT 0,
                archive INTEGER DEFAULT 0,
                vues INTEGER DEFAULT 0,
                source_url TEXT DEFAULT '',
                source_maj TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_topics_forum ON topics(forum_id, epingle DESC, maj_le DESC);
            CREATE TABLE IF NOT EXISTS posts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                auteur_id TEXT NOT NULL,
                auteur_nom TEXT NOT NULL,
                contenu TEXT NOT NULL,
                cree_le TEXT NOT NULL,
                modifie_le TEXT,
                supprime INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_posts_topic ON posts(topic_id, id);
            CREATE TABLE IF NOT EXISTS entities(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                nom TEXT NOT NULL,
                nom_norm TEXT NOT NULL,
                description TEXT DEFAULT '',
                cree_le TEXT NOT NULL,
                UNIQUE(type, nom_norm)
            );
            CREATE INDEX IF NOT EXISTS idx_entities_norm ON entities(nom_norm);
            CREATE TABLE IF NOT EXISTS mentions(
                entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                nb INTEGER DEFAULT 1,
                PRIMARY KEY(entity_id, topic_id)
            );
            CREATE TABLE IF NOT EXISTS liens(
                source INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                cible INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                type TEXT DEFAULT 'manuel',      -- manuel | wiki | auto
                cree_le TEXT NOT NULL,
                PRIMARY KEY(source, cible)
            );
            CREATE TABLE IF NOT EXISTS permissions(
                forum_id INTEGER NOT NULL REFERENCES forums(id) ON DELETE CASCADE,
                role_id TEXT NOT NULL,
                niveau INTEGER NOT NULL DEFAULT 0,   -- 0 lecture, 1 écriture, 2 modération
                PRIMARY KEY(forum_id, role_id)
            );
            """)
            # Migration douce : bases créées avant l'ajout de source_url.
            for col in ("source_url", "source_maj"):
                try:
                    c.execute(f"ALTER TABLE topics ADD COLUMN {col} TEXT DEFAULT ''")
                except sqlite3.OperationalError:
                    pass
            c.execute("CREATE INDEX IF NOT EXISTS idx_topics_source ON topics(source_url)")
            # FTS5 si disponible (recherche plein-texte performante), sinon repli LIKE.
            try:
                c.executescript("""
                CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
                    contenu, content='posts', content_rowid='id',
                    tokenize='unicode61 remove_diacritics 2');
                CREATE VIRTUAL TABLE IF NOT EXISTS topics_fts USING fts5(
                    titre, content='topics', content_rowid='id',
                    tokenize='unicode61 remove_diacritics 2');
                CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
                    INSERT INTO posts_fts(rowid, contenu) VALUES (new.id, new.contenu);
                END;
                CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE OF contenu ON posts BEGIN
                    INSERT INTO posts_fts(posts_fts, rowid, contenu) VALUES ('delete', old.id, old.contenu);
                    INSERT INTO posts_fts(rowid, contenu) VALUES (new.id, new.contenu);
                END;
                CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
                    INSERT INTO posts_fts(posts_fts, rowid, contenu) VALUES ('delete', old.id, old.contenu);
                END;
                CREATE TRIGGER IF NOT EXISTS topics_ai AFTER INSERT ON topics BEGIN
                    INSERT INTO topics_fts(rowid, titre) VALUES (new.id, new.titre);
                END;
                CREATE TRIGGER IF NOT EXISTS topics_au AFTER UPDATE OF titre ON topics BEGIN
                    INSERT INTO topics_fts(topics_fts, rowid, titre) VALUES ('delete', old.id, old.titre);
                    INSERT INTO topics_fts(rowid, titre) VALUES (new.id, new.titre);
                END;
                """)
                return True
            except sqlite3.OperationalError:
                print("⚠️ Forum : FTS5 indisponible — recherche en mode LIKE (plus lente).")
                return False

    def set_llm_extractor(self, coro):
        """Branche l'extracteur d'entités LLM : coroutine (texte) → liste de
        {"type": ..., "nom": ...}. Appelé par l'intégration bot."""
        self._llm_extractor = coro

    # ------------------------------------------------------------------
    # STRUCTURE : catégories, forums, sous-forums
    # ------------------------------------------------------------------
    def create_category(self, nom, description=""):
        with self._lock, self._conn as c:
            pos = c.execute("SELECT COALESCE(MAX(position),0)+1 FROM categories").fetchone()[0]
            cur = c.execute("INSERT INTO categories(nom, description, position, cree_le) VALUES (?,?,?,?)",
                            (nom.strip(), description.strip(), pos, _now()))
            return cur.lastrowid

    def create_forum(self, categorie_id, nom, description="", parent_id=None):
        """Un forum ; avec parent_id, c'est un SOUS-forum du forum parent."""
        with self._lock, self._conn as c:
            if not c.execute("SELECT 1 FROM categories WHERE id=?", (categorie_id,)).fetchone():
                raise ValueError(f"Catégorie {categorie_id} inconnue")
            if parent_id and not c.execute("SELECT 1 FROM forums WHERE id=?", (parent_id,)).fetchone():
                raise ValueError(f"Forum parent {parent_id} inconnu")
            pos = c.execute("SELECT COALESCE(MAX(position),0)+1 FROM forums WHERE categorie_id=?",
                            (categorie_id,)).fetchone()[0]
            cur = c.execute(
                "INSERT INTO forums(categorie_id, parent_id, nom, description, position, cree_le) "
                "VALUES (?,?,?,?,?,?)",
                (categorie_id, parent_id, nom.strip(), description.strip(), pos, _now()))
            return cur.lastrowid

    def rename(self, table, id_, nom=None, description=None):
        """Renomme/redécrit une catégorie, un forum ou un sujet."""
        assert table in ("categories", "forums", "topics")
        col = "titre" if table == "topics" else "nom"
        with self._lock, self._conn as c:
            if nom is not None:
                c.execute(f"UPDATE {table} SET {col}=? WHERE id=?", (nom.strip(), id_))
                if table == "topics":
                    c.execute("UPDATE topics SET slug=? WHERE id=?", (_slugify(nom), id_))
            if description is not None and table != "topics":
                c.execute(f"UPDATE {table} SET description=? WHERE id=?", (description.strip(), id_))

    def delete(self, table, id_):
        assert table in ("categories", "forums", "topics", "posts")
        with self._lock, self._conn as c:
            if table == "posts":
                c.execute("UPDATE posts SET supprime=1 WHERE id=?", (id_,))   # suppression douce
            else:
                c.execute(f"DELETE FROM {table} WHERE id=?", (id_,))

    def tree(self):
        """Arborescence complète : catégories → forums → sous-forums (+ stats)."""
        with self._lock:
            c = self._conn
            cats = [dict(r) for r in c.execute("SELECT * FROM categories ORDER BY position")]
            forums = [dict(r) for r in c.execute("SELECT * FROM forums ORDER BY position")]
            stats = {r["forum_id"]: (r["nb"], r["dernier"]) for r in c.execute(
                "SELECT forum_id, COUNT(*) nb, MAX(maj_le) dernier FROM topics GROUP BY forum_id")}
        by_parent = {}
        for f in forums:
            f["nb_sujets"], f["dernier"] = stats.get(f["id"], (0, None))
            by_parent.setdefault(f["parent_id"], []).append(f)

        def attach(f):
            f["sous_forums"] = [attach(sf) for sf in by_parent.get(f["id"], [])]
            return f
        for cat in cats:
            cat["forums"] = [attach(f) for f in by_parent.get(None, []) if f["categorie_id"] == cat["id"]]
        return cats

    # ------------------------------------------------------------------
    # PERMISSIONS (rôles Discord)
    # ------------------------------------------------------------------
    def set_permission(self, forum_id, role_id, niveau):
        """niveau : 0 lecture, 1 écriture, 2 modération ; None pour retirer la règle."""
        with self._lock, self._conn as c:
            if niveau is None:
                c.execute("DELETE FROM permissions WHERE forum_id=? AND role_id=?",
                          (forum_id, str(role_id)))
            else:
                c.execute("INSERT INTO permissions(forum_id, role_id, niveau) VALUES (?,?,?) "
                          "ON CONFLICT(forum_id, role_id) DO UPDATE SET niveau=excluded.niveau",
                          (forum_id, str(role_id), int(niveau)))

    def _forum_rules(self, forum_id):
        """Règles du forum, héritées du parent si le forum n'en a pas."""
        with self._lock:
            c = self._conn
            fid = forum_id
            for _ in range(6):                     # profondeur max de sous-forums : 6
                rows = c.execute("SELECT role_id, niveau FROM permissions WHERE forum_id=?",
                                 (fid,)).fetchall()
                if rows:
                    return {r["role_id"]: r["niveau"] for r in rows}
                parent = c.execute("SELECT parent_id FROM forums WHERE id=?", (fid,)).fetchone()
                if not parent or parent["parent_id"] is None:
                    return {}
                fid = parent["parent_id"]
        return {}

    def level_for(self, forum_id, role_ids, is_owner=False):
        """Niveau effectif d'un membre (liste de rôles Discord) sur un forum.
        Sans règle → forum ouvert (écriture). Le Maître a toujours tout."""
        if is_owner:
            return 2
        rules = self._forum_rules(forum_id)
        if not rules:
            return 1
        levels = [rules[str(r)] for r in role_ids if str(r) in rules]
        return max(levels) if levels else -1       # -1 : aucun accès

    # ------------------------------------------------------------------
    # SUJETS & RÉPONSES
    # ------------------------------------------------------------------
    def create_topic(self, forum_id, titre, contenu, auteur_id, auteur_nom):
        """Crée le sujet + son premier message. Renvoie (topic_id, avertissements)
        où avertissements liste les DOUBLONS potentiels détectés."""
        titre = (titre or "").strip()[:200]
        if not titre:
            raise ValueError("Titre vide")
        warns = self.find_duplicates(titre)
        with self._lock, self._conn as c:
            if not c.execute("SELECT 1 FROM forums WHERE id=?", (forum_id,)).fetchone():
                raise ValueError(f"Forum {forum_id} inconnu")
            t = _now()
            cur = c.execute(
                "INSERT INTO topics(forum_id, titre, slug, auteur_id, auteur_nom, cree_le, maj_le) "
                "VALUES (?,?,?,?,?,?,?)",
                (forum_id, titre, _slugify(titre), str(auteur_id), auteur_nom, t, t))
            tid = cur.lastrowid
        self._add_post(tid, contenu, auteur_id, auteur_nom)
        return tid, warns

    def reply(self, topic_id, contenu, auteur_id, auteur_nom):
        with self._lock:
            row = self._conn.execute("SELECT verrouille, archive FROM topics WHERE id=?",
                                     (topic_id,)).fetchone()
        if not row:
            raise ValueError(f"Sujet {topic_id} inconnu")
        if row["verrouille"]:
            raise PermissionError("Sujet verrouillé")
        if row["archive"]:
            raise PermissionError("Sujet archivé")
        return self._add_post(topic_id, contenu, auteur_id, auteur_nom)

    def _add_post(self, topic_id, contenu, auteur_id, auteur_nom):
        contenu = (contenu or "").strip()
        if not contenu:
            raise ValueError("Message vide")
        with self._lock, self._conn as c:
            cur = c.execute(
                "INSERT INTO posts(topic_id, auteur_id, auteur_nom, contenu, cree_le) "
                "VALUES (?,?,?,?,?)",
                (topic_id, str(auteur_id), auteur_nom, contenu, _now()))
            c.execute("UPDATE topics SET maj_le=? WHERE id=?", (_now(), topic_id))
            pid = cur.lastrowid
        # Enrichissements automatiques (rapides, heuristiques ; le LLM passe après,
        # côté intégration, via analyze_post_async).
        self._process_wiki_links(topic_id, contenu)
        self.index_entities(topic_id, extract_entities_heuristic(contenu))
        self._auto_link(topic_id, contenu)
        return pid

    def edit_post(self, post_id, contenu):
        with self._lock, self._conn as c:
            c.execute("UPDATE posts SET contenu=?, modifie_le=? WHERE id=?",
                      (contenu.strip(), _now(), post_id))
            row = c.execute("SELECT topic_id FROM posts WHERE id=?", (post_id,)).fetchone()
        if row:
            self._process_wiki_links(row["topic_id"], contenu)

    def set_flag(self, topic_id, verrouille=None, epingle=None, archive=None):
        """Verrouille / épingle / archive un sujet (None = ne change pas)."""
        with self._lock, self._conn as c:
            for col, val in (("verrouille", verrouille), ("epingle", epingle), ("archive", archive)):
                if val is not None:
                    c.execute(f"UPDATE topics SET {col}=? WHERE id=?", (1 if val else 0, topic_id))

    def move_topic(self, topic_id, forum_id):
        with self._lock, self._conn as c:
            c.execute("UPDATE topics SET forum_id=? WHERE id=?", (forum_id, topic_id))

    # ------------------------------------------------------------------
    # LECTURE
    # ------------------------------------------------------------------
    def breadcrumb(self, topic_id):
        """Fil d'Ariane « Catégorie › Forum › Sous-forum › Sujet »."""
        with self._lock:
            c = self._conn
            t = c.execute("SELECT titre, forum_id FROM topics WHERE id=?", (topic_id,)).fetchone()
            if not t:
                return []
            chain, fid = [t["titre"]], t["forum_id"]
            for _ in range(6):
                f = c.execute("SELECT nom, parent_id, categorie_id FROM forums WHERE id=?",
                              (fid,)).fetchone()
                if not f:
                    break
                chain.append(f["nom"])
                if f["parent_id"] is None:
                    cat = c.execute("SELECT nom FROM categories WHERE id=?",
                                    (f["categorie_id"],)).fetchone()
                    if cat:
                        chain.append(cat["nom"])
                    break
                fid = f["parent_id"]
        return list(reversed(chain))

    def list_topics(self, forum_id, page=1, per_page=25):
        """Sujets d'un forum, épinglés d'abord puis par dernière activité (façon forumactif)."""
        off = max(0, (page - 1) * per_page)
        with self._lock:
            rows = self._conn.execute(
                "SELECT t.*, (SELECT COUNT(*) FROM posts p WHERE p.topic_id=t.id AND p.supprime=0) nb_posts "
                "FROM topics t WHERE forum_id=? "
                "ORDER BY epingle DESC, maj_le DESC LIMIT ? OFFSET ?",
                (forum_id, per_page, off)).fetchall()
        return [dict(r) for r in rows]

    def get_topic(self, topic_id, with_posts=True, count_view=True):
        with self._lock, self._conn as c:
            t = c.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
            if not t:
                return None
            if count_view:
                c.execute("UPDATE topics SET vues=vues+1 WHERE id=?", (topic_id,))
            topic = dict(t)
            if with_posts:
                topic["posts"] = [dict(r) for r in c.execute(
                    "SELECT * FROM posts WHERE topic_id=? AND supprime=0 ORDER BY id", (topic_id,))]
        topic["chemin"] = self.breadcrumb(topic_id)
        topic["ref"] = f"t{topic_id}-{topic['slug']}"
        return topic

    def resolve_title(self, titre):
        """Trouve un sujet par son titre (exact normalisé, puis meilleur ratio)."""
        n = _norm(titre)
        with self._lock:
            rows = self._conn.execute("SELECT id, titre FROM topics").fetchall()
        best, best_r = None, 0.0
        for r in rows:
            if _norm(r["titre"]) == n:
                return r["id"]
            ratio = _title_ratio(titre, r["titre"])
            if ratio > best_r:
                best, best_r = r["id"], ratio
        return best if best_r >= 0.90 else None

    # ------------------------------------------------------------------
    # LIENS (wiki, manuels, automatiques) — toujours bidirectionnels
    # ------------------------------------------------------------------
    def add_link(self, source, cible, type_="manuel"):
        if source == cible:
            return False
        with self._lock, self._conn as c:
            ok = c.execute("SELECT 1 FROM topics WHERE id=?", (cible,)).fetchone()
            if not ok:
                return False
            c.execute("INSERT OR IGNORE INTO liens(source, cible, type, cree_le) VALUES (?,?,?,?)",
                      (source, cible, type_, _now()))
        return True

    def remove_link(self, source, cible):
        with self._lock, self._conn as c:
            c.execute("DELETE FROM liens WHERE (source=? AND cible=?) OR (source=? AND cible=?)",
                      (source, cible, cible, source))

    def links_of(self, topic_id):
        """Liens sortants + rétroliens, dédoublonnés, avec titre de l'autre bout."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT l.source, l.cible, l.type, t.titre FROM liens l "
                "JOIN topics t ON t.id = CASE WHEN l.source=? THEN l.cible ELSE l.source END "
                "WHERE l.source=? OR l.cible=?", (topic_id, topic_id, topic_id)).fetchall()
        seen, out = set(), []
        for r in rows:
            other = r["cible"] if r["source"] == topic_id else r["source"]
            if other in seen:
                continue
            seen.add(other)
            out.append({"id": other, "titre": r["titre"], "type": r["type"],
                        "retour": r["cible"] == topic_id})
        return out

    def _process_wiki_links(self, topic_id, contenu):
        """[[Titre]] dans un message → lien bidirectionnel vers le sujet visé."""
        for m in WIKI_RE.finditer(contenu or ""):
            cible = self.resolve_title(m.group(1).strip())
            if cible:
                self.add_link(topic_id, cible, "wiki")

    def render_wiki(self, contenu, url_base="/plateforme"):
        """Transforme les [[...]] en liens HTML internes ; les cibles inconnues
        deviennent des « liens rouges » (à créer), façon wiki."""
        def sub(m):
            titre = m.group(1).strip()
            texte = (m.group(2) or titre).strip()
            tid = self.resolve_title(titre)
            if tid:
                return f'<a class="wikilink" href="{url_base}#t{tid}" data-topic="{tid}">{texte}</a>'
            return f'<span class="wikilink missing" title="Sujet introuvable">{texte}</span>'
        return WIKI_RE.sub(sub, contenu or "")

    def _auto_link(self, topic_id, contenu):
        """Détection automatique : si le texte cite le TITRE d'un autre sujet
        (≥ 6 caractères, mot entier), on crée le lien « auto »."""
        texte_n = " " + _norm(contenu) + " "
        with self._lock:
            rows = self._conn.execute("SELECT id, titre FROM topics WHERE id != ?",
                                      (topic_id,)).fetchall()
        for r in rows:
            tn = _norm(r["titre"])
            if len(tn) >= 6 and f" {tn} " in texte_n:
                self.add_link(topic_id, r["id"], "auto")

    def autolink_html(self, topic_id, contenu, url_base="/plateforme"):
        """Rendu « hyperliens automatiques » : d'abord les [[wiki]], puis les
        titres d'autres sujets et noms d'entités cités en clair deviennent des
        liens vers le sujet correspondant (une seule fois par cible)."""
        html = self.render_wiki(contenu, url_base)
        linked = set()
        with self._lock:
            topics = self._conn.execute(
                "SELECT id, titre FROM topics WHERE id != ? ORDER BY LENGTH(titre) DESC",
                (topic_id,)).fetchall()
        for r in topics:
            if len(r["titre"]) < 6 or r["id"] in linked:
                continue
            pat = re.compile(r"(?<![\w>])(" + re.escape(r["titre"]) + r")(?![\w<])", re.IGNORECASE)
            new, n = pat.subn(
                f'<a class="wikilink auto" href="{url_base}#t{r["id"]}" data-topic="{r["id"]}">\\1</a>',
                html, count=1)
            if n:
                html, _ = new, linked.add(r["id"])
        return html

    # ------------------------------------------------------------------
    # GRAPHE DE CONNAISSANCES : entités & mentions
    # ------------------------------------------------------------------
    def index_entities(self, topic_id, entites):
        """Enregistre des entités {"type","nom"} et leurs mentions dans le sujet."""
        for e in entites or []:
            t = e.get("type") if e.get("type") in ENTITY_TYPES else "motcle"
            nom = (e.get("nom") or "").strip()[:120]
            if len(nom) < 2:
                continue
            with self._lock, self._conn as c:
                c.execute("INSERT INTO entities(type, nom, nom_norm, cree_le) VALUES (?,?,?,?) "
                          "ON CONFLICT(type, nom_norm) DO NOTHING",
                          (t, nom, _norm(nom), _now()))
                eid = c.execute("SELECT id FROM entities WHERE type=? AND nom_norm=?",
                                (t, _norm(nom))).fetchone()["id"]
                c.execute("INSERT INTO mentions(entity_id, topic_id, nb) VALUES (?,?,1) "
                          "ON CONFLICT(entity_id, topic_id) DO UPDATE SET nb=nb+1",
                          (eid, topic_id))

    async def analyze_post_async(self, topic_id, contenu):
        """Passe LLM (si branché) : entités typées correctement, puis liens auto
        entre sujets partageant assez d'entités. À appeler en tâche de fond."""
        if not self._llm_extractor:
            return 0
        try:
            entites = await self._llm_extractor(contenu)
        except Exception as e:
            print(f"⚠️ Forum : extraction LLM en panne ({e}) — l'heuristique a déjà fait le travail.")
            return 0
        self.index_entities(topic_id, entites)
        self.link_by_shared_entities(topic_id)
        return len(entites or [])

    def link_by_shared_entities(self, topic_id):
        """Crée des liens « auto » avec les sujets partageant ≥ AUTO_LINK_MIN_SHARED entités."""
        for other, shared in self._shared_entities(topic_id):
            if shared >= AUTO_LINK_MIN_SHARED:
                self.add_link(topic_id, other, "auto")

    def _shared_entities(self, topic_id):
        with self._lock:
            rows = self._conn.execute(
                "SELECT m2.topic_id o, COUNT(*) nb FROM mentions m1 "
                "JOIN mentions m2 ON m1.entity_id=m2.entity_id AND m2.topic_id != m1.topic_id "
                "WHERE m1.topic_id=? GROUP BY m2.topic_id ORDER BY nb DESC", (topic_id,)).fetchall()
        return [(r["o"], r["nb"]) for r in rows]

    def entities_of(self, topic_id):
        with self._lock:
            rows = self._conn.execute(
                "SELECT e.id, e.type, e.nom, m.nb FROM mentions m JOIN entities e ON e.id=m.entity_id "
                "WHERE m.topic_id=? ORDER BY m.nb DESC, e.nom", (topic_id,)).fetchall()
        return [dict(r) for r in rows]

    def topics_of_entity(self, entity_id):
        with self._lock:
            rows = self._conn.execute(
                "SELECT t.id, t.titre, m.nb FROM mentions m JOIN topics t ON t.id=m.topic_id "
                "WHERE m.entity_id=? ORDER BY m.nb DESC", (entity_id,)).fetchall()
        return [dict(r) for r in rows]

    def graph(self, topic_id=None, depth=1, max_nodes=60):
        """Graphe {nodes, edges} : global (topic_id=None) ou voisinage d'un sujet.
        Nœuds = sujets ; arêtes = liens. Les entités les plus citées du voisinage
        sont jointes comme nœuds « entité » pour visualiser le tissu de connaissances."""
        with self._lock:
            c = self._conn
            if topic_id is None:
                tids = [r["id"] for r in c.execute(
                    "SELECT id FROM topics ORDER BY maj_le DESC LIMIT ?", (max_nodes,))]
            else:
                tids, frontier = {topic_id}, {topic_id}
                for _ in range(depth):
                    if not frontier:
                        break
                    q = ",".join("?" * len(frontier))
                    rows = c.execute(f"SELECT source, cible FROM liens WHERE source IN ({q}) "
                                     f"OR cible IN ({q})", (*frontier, *frontier)).fetchall()
                    nxt = {x for r in rows for x in (r["source"], r["cible"])} - tids
                    tids |= nxt
                    frontier = nxt
                tids = list(tids)[:max_nodes]
            q = ",".join("?" * len(tids)) or "0"
            nodes = [{"id": f"t{r['id']}", "tid": r["id"], "label": r["titre"], "kind": "sujet"}
                     for r in c.execute(f"SELECT id, titre FROM topics WHERE id IN ({q})", tids)]
            edges = [{"a": f"t{r['source']}", "b": f"t{r['cible']}", "type": r["type"]}
                     for r in c.execute(
                         f"SELECT source, cible, type FROM liens "
                         f"WHERE source IN ({q}) AND cible IN ({q})", (*tids, *tids))]
            ents = c.execute(
                f"SELECT e.id, e.nom, e.type, COUNT(*) nb FROM mentions m "
                f"JOIN entities e ON e.id=m.entity_id WHERE m.topic_id IN ({q}) "
                f"GROUP BY e.id HAVING nb >= 2 ORDER BY nb DESC LIMIT 25", tids).fetchall()
            for e in ents:
                nodes.append({"id": f"e{e['id']}", "label": e["nom"], "kind": e["type"]})
                for r in c.execute(f"SELECT topic_id FROM mentions WHERE entity_id=? "
                                   f"AND topic_id IN ({q})", (e["id"], *tids)):
                    edges.append({"a": f"e{e['id']}", "b": f"t{r['topic_id']}", "type": "mention"})
        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # COHÉRENCE : doublons & similaires
    # ------------------------------------------------------------------
    def find_duplicates(self, titre, exclude_id=None):
        """Sujets dont le titre est quasi identique (doublons probables)."""
        out = []
        with self._lock:
            rows = self._conn.execute("SELECT id, titre FROM topics").fetchall()
        for r in rows:
            if r["id"] == exclude_id:
                continue
            ratio = _title_ratio(titre, r["titre"])
            if ratio >= SIMILAR_TITLE_RATIO:
                out.append({"id": r["id"], "titre": r["titre"], "ratio": round(ratio, 2)})
        return sorted(out, key=lambda x: -x["ratio"])[:5]

    def related_topics(self, topic_id, limit=SUGGESTIONS_MAX):
        """Suggestions de sujets connexes : entités partagées (fort), liens de
        liens (moyen), similarité de titre (faible). Score composite."""
        scores = {}
        for other, shared in self._shared_entities(topic_id):
            if shared >= RELATED_MIN_SHARED:
                scores[other] = scores.get(other, 0) + shared * 3
        direct = {l["id"] for l in self.links_of(topic_id)}
        for l in list(direct):
            for l2 in self.links_of(l):
                if l2["id"] not in direct and l2["id"] != topic_id:
                    scores[l2["id"]] = scores.get(l2["id"], 0) + 2
        me = self.get_topic(topic_id, with_posts=False, count_view=False)
        if me:
            with self._lock:
                rows = self._conn.execute("SELECT id, titre FROM topics WHERE id != ?",
                                          (topic_id,)).fetchall()
            for r in rows:
                ratio = _title_ratio(me["titre"], r["titre"])
                if ratio >= 0.55:
                    scores[r["id"]] = scores.get(r["id"], 0) + ratio * 2
        scores.pop(topic_id, None)
        for d in direct:
            scores.pop(d, None)                      # déjà liés : inutile de les suggérer
        top = sorted(scores.items(), key=lambda kv: -kv[1])[:limit]
        out = []
        with self._lock:
            for tid, sc in top:
                r = self._conn.execute("SELECT titre FROM topics WHERE id=?", (tid,)).fetchone()
                if r:
                    out.append({"id": tid, "titre": r["titre"], "score": round(sc, 1)})
        return out

    # ------------------------------------------------------------------
    # RECHERCHE
    # ------------------------------------------------------------------
    def search(self, requete, limit=25):
        """Moteur de recherche : plein-texte (FTS5 ou LIKE) sur titres + messages,
        PLUS recherche par entité (« lieu:Ambre », « personnage:X ») et par
        relations (« avec:Sujet A avec:Sujet B » → sujets liés aux deux)."""
        requete = (requete or "").strip()
        if not requete:
            return []
        # -- filtres entité / relation extraits de la requête --------------
        ent_filters, rel_filters, words = [], [], []
        for tok in re.findall(r'(\w+):"([^"]+)"|(\w+):(\S+)|(\S+)', requete):
            key = tok[0] or tok[2]
            val = tok[1] or tok[3]
            if key and key.lower() in ENTITY_TYPES:
                ent_filters.append((key.lower(), val))
            elif key and key.lower() in ("avec", "lie", "lié"):
                rel_filters.append(val)
            elif key:
                words.append(f"{key}:{val}")
            else:
                words.append(tok[4])
        texte = " ".join(words).strip()

        scored = {}                                   # topic_id -> score

        # -- plein-texte ---------------------------------------------------
        if texte:
            with self._lock:
                c = self._conn
                if self._fts:
                    fts_q = " OR ".join(f'"{w}"' for w in _tokens(texte)) or f'"{texte}"'
                    try:
                        for r in c.execute(
                                "SELECT rowid, bm25(topics_fts) s FROM topics_fts "
                                "WHERE topics_fts MATCH ? ORDER BY s LIMIT ?", (fts_q, limit * 2)):
                            scored[r["rowid"]] = scored.get(r["rowid"], 0) + 10 - min(9, abs(r["s"]))
                        for r in c.execute(
                                "SELECT p.topic_id t, bm25(posts_fts) s FROM posts_fts "
                                "JOIN posts p ON p.id=posts_fts.rowid "
                                "WHERE posts_fts MATCH ? ORDER BY s LIMIT ?", (fts_q, limit * 3)):
                            scored[r["t"]] = scored.get(r["t"], 0) + 6 - min(5, abs(r["s"]))
                    except sqlite3.OperationalError:
                        pass                           # requête FTS invalide → repli LIKE
                if not scored:
                    like = f"%{texte}%"
                    for r in c.execute("SELECT id FROM topics WHERE titre LIKE ? LIMIT ?",
                                       (like, limit)):
                        scored[r["id"]] = scored.get(r["id"], 0) + 8
                    for r in c.execute(
                            "SELECT DISTINCT topic_id FROM posts WHERE contenu LIKE ? LIMIT ?",
                            (like, limit)):
                        scored[r["topic_id"]] = scored.get(r["topic_id"], 0) + 4

        # -- entités -------------------------------------------------------
        for etype, val in ent_filters:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT m.topic_id, m.nb FROM mentions m JOIN entities e ON e.id=m.entity_id "
                    "WHERE e.type=? AND e.nom_norm LIKE ?", (etype, f"%{_norm(val)}%")).fetchall()
            hit = {r["topic_id"]: r["nb"] for r in rows}
            if scored or texte:
                for tid, nb in hit.items():
                    scored[tid] = scored.get(tid, 0) + 5 + nb
            else:
                scored = {tid: 5 + nb for tid, nb in hit.items()}
        # sans texte, exiger TOUTES les entités demandées (intersection)
        if ent_filters and not texte:
            for etype, val in ent_filters:
                with self._lock:
                    keep = {r["topic_id"] for r in self._conn.execute(
                        "SELECT m.topic_id FROM mentions m JOIN entities e ON e.id=m.entity_id "
                        "WHERE e.type=? AND e.nom_norm LIKE ?", (etype, f"%{_norm(val)}%"))}
                scored = {t: s for t, s in scored.items() if t in keep}

        # -- relations : sujets liés à TOUTES les cibles « avec: » ----------
        for cible in rel_filters:
            tid = self.resolve_title(cible)
            if not tid:
                continue
            voisins = {l["id"] for l in self.links_of(tid)}
            if scored:
                scored = {t: s + 4 for t, s in scored.items() if t in voisins}
            else:
                scored = {t: 4 for t in voisins}

        top = sorted(scored.items(), key=lambda kv: -kv[1])[:limit]
        out = []
        with self._lock:
            for tid, sc in top:
                r = self._conn.execute(
                    "SELECT id, titre, forum_id, maj_le FROM topics WHERE id=?", (tid,)).fetchone()
                if r:
                    d = dict(r)
                    d["score"] = round(sc, 1)
                    d["chemin"] = " › ".join(self.breadcrumb(tid)[:-1])
                    out.append(d)
        return out

    def theme_index(self):
        """Index par thème : chaque entité et la liste des sujets qui la citent
        (trié par nombre de sujets décroissant). C'est l'index « wiki » consultable."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT e.id, e.type, e.nom, COUNT(m.topic_id) nb FROM entities e "
                "JOIN mentions m ON m.entity_id=e.id GROUP BY e.id "
                "HAVING nb >= 1 ORDER BY nb DESC, e.nom").fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # IMPORT D'UN FORUM EXTERNE (copie interne → plateforme)
    # ------------------------------------------------------------------
    IMPORT_CATEGORY = "Orbis Naturae"
    IMPORT_FALLBACK_FORUM = "Sans rubrique"

    def _ensure_path(self, chemin):
        """« Rubrique › Sous-forum › … » → crée (ou retrouve) catégorie + forums
        emboîtés. Le 1er élément devient la catégorie ; sans chemin, tout va dans
        IMPORT_CATEGORY / IMPORT_FALLBACK_FORUM. Renvoie l'id du forum final."""
        parts = [p.strip() for p in (chemin or "").split("›") if p.strip()]
        if not parts:
            parts = [self.IMPORT_CATEGORY, self.IMPORT_FALLBACK_FORUM]
        elif len(parts) == 1:
            parts = [self.IMPORT_CATEGORY] + parts
        cat_nom, forums = parts[0], parts[1:]
        with self._lock, self._conn as c:
            row = c.execute("SELECT id FROM categories WHERE nom=?", (cat_nom,)).fetchone()
        cid = row["id"] if row else self.create_category(cat_nom)
        fid, parent = None, None
        for nom in forums[:6]:
            with self._lock:
                q = ("SELECT id FROM forums WHERE categorie_id=? AND nom=? AND parent_id IS ?"
                     if parent is None else
                     "SELECT id FROM forums WHERE categorie_id=? AND nom=? AND parent_id=?")
                row = self._conn.execute(q, (cid, nom, parent)).fetchone()
            fid = row["id"] if row else self.create_forum(cid, nom, parent_id=parent)
            parent = fid
        return fid

    def topic_by_source(self, source_url):
        with self._lock:
            row = self._conn.execute("SELECT id FROM topics WHERE source_url=?",
                                     (source_url,)).fetchone()
        return row["id"] if row else None

    def import_external_topic(self, source_url, titre, chemin, contenu,
                              auteur_nom="Orbis Naturae", verrouille=True, source_maj=""):
        """Importe (ou MET À JOUR) une fiche du forum externe comme sujet.
        Idempotent : la même source_url ne crée jamais de doublon, et si la date
        de copie (source_maj) n'a pas changé, on ne touche à rien — c'est ce qui
        rend la synchro périodique quasi gratuite. Le contenu est posé BRUT :
        appeler reindex_topic() sur les sujets créés/modifiés.
        Renvoie (topic_id, 'cree'|'maj'|'inchange')."""
        titre = (titre or "").strip()[:200] or "(sans titre)"
        contenu = (contenu or "").strip() or "(fiche vide)"
        tid = self.topic_by_source(source_url)
        if tid is None:
            fid = self._ensure_path(chemin)
            t = _now()
            with self._lock, self._conn as c:
                cur = c.execute(
                    "INSERT INTO topics(forum_id, titre, slug, auteur_id, auteur_nom, cree_le, "
                    "maj_le, verrouille, source_url, source_maj) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (fid, titre, _slugify(titre), "import", auteur_nom, t, t,
                     1 if verrouille else 0, source_url, source_maj or ""))
                tid = cur.lastrowid
                c.execute("INSERT INTO posts(topic_id, auteur_id, auteur_nom, contenu, cree_le) "
                          "VALUES (?,?,?,?,?)", (tid, "import", auteur_nom, contenu, t))
            return tid, "cree"
        # Fiche inchangée depuis la dernière synchro ? On s'arrête là (rapide).
        if source_maj:
            with self._lock:
                row = self._conn.execute("SELECT source_maj FROM topics WHERE id=?",
                                         (tid,)).fetchone()
            if row and row["source_maj"] == source_maj:
                return tid, "inchange"
        # Sujet déjà importé : on rafraîchit titre, rubrique et contenu si besoin.
        with self._lock, self._conn as c:
            old = c.execute("SELECT t.titre, t.forum_id, p.id pid, p.contenu FROM topics t "
                            "JOIN posts p ON p.topic_id=t.id WHERE t.id=? "
                            "ORDER BY p.id LIMIT 1", (tid,)).fetchone()
        changed = False
        if old and old["contenu"] != contenu:
            with self._lock, self._conn as c:
                c.execute("UPDATE posts SET contenu=?, modifie_le=? WHERE id=?",
                          (contenu, _now(), old["pid"]))
                c.execute("UPDATE topics SET maj_le=? WHERE id=?", (_now(), tid))
            changed = True
        if old and old["titre"] != titre:
            self.rename("topics", tid, nom=titre)
            changed = True
        fid = self._ensure_path(chemin)
        if old and old["forum_id"] != fid:
            self.move_topic(tid, fid)
            changed = True
        with self._lock, self._conn as c:
            c.execute("UPDATE topics SET source_maj=? WHERE id=?", (source_maj or "", tid))
        return tid, ("maj" if changed else "inchange")

    def reindex_topic(self, topic_id):
        """Reconstruit mentions + liens wiki/auto d'UN sujet (après création ou
        mise à jour par la synchro) — sans repasser toute la base au crible."""
        with self._lock, self._conn as c:
            c.execute("DELETE FROM mentions WHERE topic_id=?", (topic_id,))
            c.execute("DELETE FROM liens WHERE type='auto' AND (source=? OR cible=?)",
                      (topic_id, topic_id))
            posts = c.execute("SELECT contenu FROM posts WHERE topic_id=? AND supprime=0",
                              (topic_id,)).fetchall()
        texte = "\n".join(p["contenu"] for p in posts)
        self.index_entities(topic_id, extract_entities_heuristic(texte))
        self._process_wiki_links(topic_id, texte)
        self._auto_link(topic_id, texte)
        self.link_by_shared_entities(topic_id)

    def import_links(self, mapping, liens_par_url):
        """Retisse les liens de la copie externe : mapping {source_url: topic_id},
        liens_par_url {source_url: [url_cible, …]}. Renvoie le nb de liens créés."""
        n = 0
        for src, cibles in (liens_par_url or {}).items():
            a = mapping.get(src)
            if not a:
                continue
            for cible in cibles:
                b = mapping.get(cible)
                if b and self.add_link(a, b, "manuel"):
                    n += 1
        return n

    # ------------------------------------------------------------------
    # STATISTIQUES & MAINTENANCE
    # ------------------------------------------------------------------
    def stats(self):
        with self._lock:
            c = self._conn
            g = lambda q: c.execute(q).fetchone()[0]
            return {
                "categories": g("SELECT COUNT(*) FROM categories"),
                "forums": g("SELECT COUNT(*) FROM forums"),
                "sujets": g("SELECT COUNT(*) FROM topics"),
                "messages": g("SELECT COUNT(*) FROM posts WHERE supprime=0"),
                "entites": g("SELECT COUNT(*) FROM entities"),
                "liens": g("SELECT COUNT(*) FROM liens"),
                "fts": self._fts,
            }

    def reindex_all(self):
        """Reconstruit mentions + liens auto pour TOUS les sujets (maintenance).
        Utile après import ou changement d'heuristique."""
        with self._lock, self._conn as c:
            c.execute("DELETE FROM mentions")
            c.execute("DELETE FROM liens WHERE type='auto'")
            topics = [dict(r) for r in c.execute("SELECT id FROM topics")]
        for t in topics:
            with self._lock:
                posts = self._conn.execute(
                    "SELECT contenu FROM posts WHERE topic_id=? AND supprime=0",
                    (t["id"],)).fetchall()
            texte = "\n".join(p["contenu"] for p in posts)
            self.index_entities(t["id"], extract_entities_heuristic(texte))
            self._process_wiki_links(t["id"], texte)
            self._auto_link(t["id"], texte)
        for t in topics:
            self.link_by_shared_entities(t["id"])
        return len(topics)

    def export_json(self):
        """Export complet (sauvegarde/migration) au format JSON."""
        with self._lock:
            c = self._conn
            dump = {}
            for table in ("categories", "forums", "topics", "posts", "entities",
                          "mentions", "liens", "permissions"):
                dump[table] = [dict(r) for r in c.execute(f"SELECT * FROM {table}")]
        return json.dumps(dump, ensure_ascii=False, indent=1)

    def close(self):
        with self._lock:
            self._conn.close()