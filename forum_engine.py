"""
forum_engine.py — Lecture structurée des sujets et moteur de recherche du forum.

Module PUR : ni réseau, ni Discord, ni fichier. bot.py lui donne du HTML ou le texte de la
copie interne ; il rend des messages structurés et des résultats classés. Trois briques :

  1. LIRE UN SUJET — `parse_topic_page(html)` découpe une page de sujet en MESSAGES
     (auteur, date, texte) au lieu d'un bloc de texte indistinct : le message d'ouverture et
     chaque réponse restent séparés et attribués. `render_posts` / `split_posts` font l'aller-
     retour entre ces messages et le texte stocké dans la copie interne.

  2. CHERCHER — `ForumIndex` est un vrai petit moteur de recherche sur TOUT le texte copié
     (pas seulement les titres) : découpage en passages, classement BM25, poids du titre et de
     la rubrique, singulier/pluriel, variantes d'un nom (Skaldia / Skaldien), fautes de frappe,
     expressions entre guillemets, et un extrait autour des mots trouvés — comme un moteur web.

  3. CHOISIR QUOI CITER — `meilleurs_passages` extrait d'un long sujet les passages qui
     répondent à une question, quand tout ne tient pas dans le budget.
"""
import math
import os
import re
from array import array
from difflib import get_close_matches
from html.parser import HTMLParser

from textutils import _fold, _stem

# ============================================================
# 1. LIRE UN SUJET : la page → des messages
# ============================================================
# Un message se reconnaît à son conteneur : id="post-29" (AwesomeBB), id="p29" (phpBB3,
# ModernBB, punBB, Invision) ou une classe « post--29 » (phpBB2). À l'intérieur, on cherche le
# corps, l'auteur et la date par leurs classes usuelles sur Forumactif.
_POST_ID_RE = re.compile(r"^(?:post-?|p)(\d+)$")
_POST_CLASS_RE = re.compile(r"^post--(\d+)$")
_CONTENT_CLASSES = {"post-content", "entry-content", "post-entry", "content"}
_BODY_CLASSES = {"postbody", "post-body"}                  # repli : corps + en-tête mêlés
_AUTHOR_CLASSES = {"post-author-name", "postprofile-name", "username", "author-name", "author", "name"}
_DATE_CLASSES = {"post-date", "topic-date", "posttime", "date"}
_IGNORED_CLASSES = ("signature", "sig-content", "post-buttons", "post-footer", "dropdown")
_VOID_TAGS = {"br", "img", "hr", "input", "meta", "link", "area", "base", "col", "embed",
              "source", "track", "wbr"}
_BLOCK_TAGS = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "ul",
               "ol", "table", "dd", "dt", "section", "article", "pre"}
_SKIP_TAGS = {"script", "style", "noscript", "template", "select", "button", "svg"}
MESSAGE_SANS_TEXTE = "(message sans texte"      # début du texte donné à un message sans texte
_DATE_HINT_RE = re.compile(
    r"(?i)\b(?:(?:lun|mar|mer|jeu|ven|sam|dim)(?:di|credi|edi|dredi|anche)?\b|aujourd'hui|hier\b|"
    r"\d{1,2}\s+(?:jan|f[ée]v|mars|avr|mai|juin|juil|ao[uû]|sep|oct|nov|d[ée]c)|"
    r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})")


def _clean_text(parts):
    txt = "".join(parts).replace("\xa0", " ")
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r" *\n *", "\n", txt)
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


class _TopicParser(HTMLParser):
    """Découpe une page de sujet en messages. Tolérant au HTML bancal des forums : une balise
    fermante orpheline est ignorée, une balise non fermée est refermée par son parent."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []            # [(balise, {rôles ouverts par cet élément})]
        self.actifs = {}           # rôle -> nombre d'éléments ouverts qui le portent
        self.posts = []
        self.post = None           # message en cours
        self.post_depth = 0
        self.skip = 0              # profondeur dans <script>, <style>…
        self.titre = []
        self.lien = None           # lien en cours dans le corps : [href, [texte]]

    # -- structure ---------------------------------------------------------------------
    def _roles(self, tag, attrs):
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        roles = set()
        if self.post is None:
            pid = None
            m = _POST_ID_RE.match(a.get("id") or "")
            if m and any(c.startswith("post") for c in classes):
                pid = m.group(1)
            else:
                pid = next((mc.group(1) for mc in map(_POST_CLASS_RE.match, classes) if mc), None)
            if pid is not None:
                self.post = {"id": int(pid), "content": [], "body": [], "all": [],
                             "auteur": [], "date": [], "liens": [], "corps_vu": False, "images": 0}
                self.post_depth = len(self.stack) + 1
                roles.add("post")
            elif tag == "h1" and not self.titre:
                roles.add("titre")
            return roles
        if any(marque in c for c in classes for marque in _IGNORED_CLASSES):
            roles.add("ignore")
        if classes & _CONTENT_CLASSES:
            roles.add("content")
            self.post["corps_vu"] = True
        if classes & _BODY_CLASSES:
            roles.add("body")
        if classes & _AUTHOR_CLASSES:
            roles.add("auteur")
        if classes & _DATE_CLASSES:
            roles.add("date")
        if tag == "blockquote":
            roles.add("citation")
        return roles

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self.skip += 1
            self.stack.append((tag, {"skip"}))
            return
        if tag in _VOID_TAGS:
            if tag in ("br", "hr"):
                self._emit("\n")
            elif tag == "img" and self.post is not None and self.actifs.get("content"):
                self.post["images"] += 1
            return
        roles = self._roles(tag, attrs)
        if tag in _BLOCK_TAGS:
            self._emit("\n")
        if "citation" in roles:
            self._emit("\n[citation] ")
        if tag == "a" and self.post is not None and self.actifs.get("content"):
            self.lien = [dict(attrs).get("href") or "", []]
        self.stack.append((tag, roles))
        for r in roles:
            self.actifs[r] = self.actifs.get(r, 0) + 1

    def handle_startendtag(self, tag, attrs):          # <br />, <img … />, <div … />
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS or not any(t == tag for t, _ in self.stack):
            return                                    # fermante orpheline (« par X</a> »)
        while self.stack:
            t, roles = self.stack.pop()
            if "skip" in roles:
                self.skip -= 1
            if "citation" in roles:
                self._emit(" [fin de citation]\n")
            for r in roles - {"skip"}:
                self.actifs[r] -= 1
            if t in _BLOCK_TAGS:
                self._emit("\n")
            if t == "a" and self.lien is not None:
                href, morceaux = self.lien
                if href and self.post is not None:
                    self.post["liens"].append((href, "".join(morceaux).strip()))
                self.lien = None
            if self.post is not None and len(self.stack) < self.post_depth:
                self._close_post()
            if t == tag:
                break

    # -- texte -------------------------------------------------------------------------
    def _emit(self, s):
        if self.skip:
            return
        if self.post is None:
            if self.actifs.get("titre"):
                self.titre.append(s)
            return
        p = self.post
        if self.actifs.get("ignore"):
            return
        if self.actifs.get("auteur") and not self.actifs.get("content"):
            p["auteur"].append(s)
        if self.actifs.get("date") and not self.actifs.get("content"):
            p["date"].append(s)
        if self.actifs.get("content"):
            p["content"].append(s)
        if self.actifs.get("body"):
            p["body"].append(s)
        p["all"].append(s)

    def handle_data(self, data):
        if self.lien is not None and not self.skip:
            self.lien[1].append(data)
        self._emit(data)

    def _close_post(self):
        p, self.post = self.post, None
        if not p["id"]:                               # bloc publicitaire (post-0)
            return
        if p["corps_vu"]:
            # Le corps du message a été trouvé : c'est LUI le texte, même vide (une fiche qui ne
            # contient qu'une image ne doit pas être remplacée par le profil de son auteur).
            texte = _clean_text(p["content"])
            if not texte:
                texte = MESSAGE_SANS_TEXTE + (f" — {p['images']} image(s) seulement)" if p["images"] else ")")
        else:
            texte = _clean_text(p["body"]) or _clean_text(p["all"])
        if not texte:
            return
        auteur = _clean_text(p["auteur"]).split("\n")[0].strip()
        auteur = re.sub(r"(?i)^(par|de|by)\s+", "", auteur).strip()
        date = _clean_text(p["date"]).split("\n")[0].strip()
        m = _DATE_HINT_RE.search(auteur)              # « par Untel Dim 12 Jan 2020 » (phpBB3)
        if m and m.start() > 0:
            if not date:
                date = auteur[m.start():].strip()
            auteur = re.sub(r"(?i)\s+(le|on)$", "", auteur[:m.start()].strip(" -–—,·|"))
        self.posts.append({"id": p["id"], "auteur": auteur[:60], "date": date[:60],
                           "texte": texte, "liens": p["liens"]})

    def close(self):
        super().close()
        if self.post is not None:
            self._close_post()


def parse_topic_page(html):
    """Découpe UNE page de sujet. Renvoie {"titre", "posts": [{id, auteur, date, texte, liens}]}.
    `posts` est vide si la page n'a pas la structure d'un sujet de forum (l'appelant retombe
    alors sur le texte brut de la page)."""
    parser = _TopicParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:                                 # HTML trop abîmé : repli sur le texte brut
        return {"titre": "", "posts": []}
    return {"titre": _clean_text(parser.titre), "posts": parser.posts}


# --- Aller-retour messages ↔ texte de la copie interne -------------------------------------
_ENTETE_RE = re.compile(r"^── Message (\d+)(?:/(\d+))? · (.*?) · (.*?) ──[ \t]*$", re.MULTILINE)


def render_posts(posts, total=None, debut=1):
    """Texte d'un sujet, message par message, chacun précédé d'un en-tête
    « ── Message 2/5 · Auteur · date ── ». C'est ce format que stocke la copie interne."""
    total = total or (debut - 1 + len(posts))
    blocs = []
    for i, p in enumerate(posts, debut):
        auteur = (p.get("auteur") or "auteur inconnu").replace(" · ", " - ")
        date = (p.get("date") or "date inconnue").replace(" · ", " - ")
        blocs.append(f"── Message {i}/{total} · {auteur} · {date} ──\n{(p.get('texte') or '').strip()}")
    return "\n\n".join(blocs)


def split_posts(contenu):
    """Inverse de render_posts. Un texte sans en-tête (ancienne copie) est rendu comme un seul
    message sans auteur. Renvoie [{n, auteur, date, texte}]."""
    contenu = contenu or ""
    marques = list(_ENTETE_RE.finditer(contenu))
    if not marques:
        return [{"n": 1, "auteur": "", "date": "", "texte": contenu.strip()}] if contenu.strip() else []
    posts = []
    for i, m in enumerate(marques):
        fin = marques[i + 1].start() if i + 1 < len(marques) else len(contenu)
        auteur, date = m.group(3).strip(), m.group(4).strip()
        posts.append({"n": int(m.group(1)),
                      "auteur": "" if auteur == "auteur inconnu" else auteur,
                      "date": "" if date == "date inconnue" else date,
                      "texte": contenu[m.end():fin].strip()})
    return posts


# ============================================================
# 2. CHERCHER : le moteur
# ============================================================
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_MOT_RE = re.compile(r"[^\W\d_]{4,}")                       # un mot d'au moins 4 lettres, casse conservée
# Mots vides : articles, prépositions, auxiliaires… et les mots de la QUESTION elle-même
# (« dis-moi tout ce que tu sais sur… »), qui ne disent rien de ce qu'on cherche.
STOPWORDS = frozenset("""
a ai aie ait as au aux avec avaient avait avoir c ca ce cela ces cet cette ceux chez comme d dans
de des du elle elles en es est et etaient etait ete etre eu eux il ils j je l la le les leur
leurs lui m ma mais me meme mes moi mon n ne ni nos notre nous on ont ou par pas plus pour qu
que quel quelle quelles quels qui quoi s sa sans se sera ses si son sont sur t ta te tes toi
ton tous tout toute toutes tres tu un une vos votre vous y
comment pourquoi quand combien dont donc alors aussi ainsi puis car or ici la
dis dire dit parle parler raconte raconter explique expliquer sais sait savoir connais connait
connaitre cherche chercher trouve trouver donne donner montre montrer peux peut pouvoir veux
veut fais fait faire infos info information informations propos sujet sujets forum
""".split())


def racine(mot):
    """Racine LÉGÈRE d'un mot déjà plié (sans accents, minuscules) : pluriel, féminin, infinitif.
    Volontairement prudente — elle rapproche « Linnorms » de « Linnorm », « Skaldienne » de
    « Skaldien », sans fondre ensemble des mots sans rapport."""
    n = len(mot)
    if n < 4 or mot.isdigit():
        return mot
    if mot.endswith("x"):
        # chevaux → cheval, mais châteaux → château (les « -eaux » ne sont pas des « -al »)
        mot = mot[:-3] + "al" if (n >= 6 and mot.endswith("aux") and not mot.endswith("eaux")) else mot[:-1]
    elif mot.endswith("s"):
        mot = mot[:-1]
    if len(mot) >= 6:
        if mot.endswith("r"):
            mot = mot[:-1]
        if mot.endswith("e"):
            mot = mot[:-1]
        if len(mot) >= 2 and mot[-1] == mot[-2]:
            mot = mot[:-1]
    return mot


def termes(texte):
    """Racines significatives d'un texte, dans l'ordre, mots vides écartés."""
    return [racine(t) for t in _TOKEN_RE.findall(_fold(texte or ""))
            if len(t) >= 2 and t not in STOPWORDS]


def famille(mot):
    """Racine LARGE d'un mot plié : celle de sa famille (fonder, fondé, fondation, fondateur →
    « fond »). Trop gourmande pour servir de clé d'index — elle ne sert qu'à proposer, avec un
    poids réduit, les mots de la même famille que ceux de la question. '' si elle est trop courte
    pour être fiable."""
    f = _stem(mot)
    return f if len(f) >= 4 and len(mot) >= 5 else ""


def _distance(a, b, maxi):
    """Distance d'édition entre a et b, abandonnée dès qu'elle dépasse `maxi`."""
    if abs(len(a) - len(b)) > maxi:
        return maxi + 1
    prec = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cour = [i]
        for j, cb in enumerate(b, 1):
            cour.append(min(prec[j] + 1, cour[j - 1] + 1, prec[j - 1] + (ca != cb)))
        if min(cour) > maxi:
            return maxi + 1
        prec = cour
    return prec[-1]


PASSAGE_MAX = 900           # taille visée d'un passage (caractères)
_BM25_K1, _BM25_B = 1.4, 0.6
# Poids des champs. Le DÉBUT du titre (avant le tiret : « Tasglev — la ville noire ») nomme
# l'entité dont parle la fiche ; ce qui suit n'en est qu'un attribut (« moniale d'Aémée »).
_POIDS_TETE, _POIDS_TITRE, _POIDS_MOTS, _POIDS_CHEMIN = 4.0, 2.2, 1.2, 1.0
_TETE_TITRE_RE = re.compile(r"\s[—–-]\s|[:,(\[]")


def _decouper(texte, maxi=PASSAGE_MAX):
    """Découpe un message en passages d'au plus ~maxi caractères, sur les paragraphes puis les
    phrases : un passage reste une unité de sens, jamais une coupe au milieu d'un mot."""
    passages, courant = [], ""
    for para in re.split(r"\n\s*\n", texte or ""):
        para = para.strip()
        if not para:
            continue
        morceaux = [para]
        if len(para) > maxi:
            morceaux, tampon = [], ""
            for phrase in re.split(r"(?<=[.!?…»])\s+|\n", para):
                while len(phrase) > maxi:                       # phrase interminable : coupe dure
                    coupe = phrase.rfind(" ", 0, maxi)
                    coupe = coupe if coupe > maxi // 2 else maxi
                    morceaux.append((tampon + " " + phrase[:coupe]).strip() if tampon else phrase[:coupe])
                    tampon, phrase = "", phrase[coupe:].strip()
                if len(tampon) + len(phrase) + 1 > maxi and tampon:
                    morceaux.append(tampon)
                    tampon = phrase
                else:
                    tampon = (tampon + " " + phrase).strip()
            if tampon:
                morceaux.append(tampon)
        for m in morceaux:
            if courant and len(courant) + len(m) + 2 > maxi:
                passages.append(courant)
                courant = m
            else:
                courant = (courant + "\n\n" + m) if courant else m
    if courant:
        passages.append(courant)
    return passages


class ForumIndex:
    """Index plein texte de la copie du forum. Construit d'un coup (`build`), interrogé par
    `search`. Compact : les listes d'occurrences sont des tableaux d'entiers."""

    def __init__(self):
        self.docs = []            # [{url, titre, chemin, maj, copie, n_posts}]
        self.passages = []        # [(doc_i, n_message, auteur, texte)]
        self._post = {}           # racine -> (array pids, array tfs)
        self._plen = array("I")   # longueur (en racines) de chaque passage
        self._champs = {}         # racine -> {doc_i: poids}  (titre / rubrique / mots-clés)
        self._df_doc = {}         # racine -> nombre de sujets qui la contiennent
        self._titre_plie = []     # titre plié de chaque sujet (recherche d'expression)
        self._par_doc = {}        # doc_i -> [pids]
        self._prefixes = None     # 3 premières lettres -> [racines]  (construit à la demande)
        self._familles = {}       # racine large -> {racines de la même famille de mots}
        self._casse = {}          # mot plié -> [nb d'occurrences sans majuscule, avec majuscule]
        self._avgdl = 1.0

    # -- construction ------------------------------------------------------------------
    @classmethod
    def build(cls, fiches):
        """fiches : itérable de dicts {url, titre, chemin, mots, contenu, maj}. `contenu` peut
        être vide (sujet cartographié mais pas encore copié) : il reste trouvable par son titre."""
        idx = cls()
        vus_par_doc = []
        memo = {}                 # mot plié -> racine (chaque mot n'est analysé qu'une fois)
        for f in fiches:
            url = f.get("url")
            if not url:
                continue
            doc_i = len(idx.docs)
            messages = split_posts(f.get("contenu") or "")
            idx.docs.append({"url": url, "titre": (f.get("titre") or "").strip(),
                             "chemin": (f.get("chemin") or "").strip(), "maj": f.get("maj") or "",
                             "copie": bool(messages), "n_posts": len(messages)})
            idx._titre_plie.append(_fold(f.get("titre") or ""))
            vus = set()
            titre = (f.get("titre") or "").strip()
            for champ, poids in ((_TETE_TITRE_RE.split(titre, maxsplit=1)[0], _POIDS_TETE),
                                 (titre, _POIDS_TITRE), (f.get("mots"), _POIDS_MOTS),
                                 (f.get("chemin"), _POIDS_CHEMIN)):
                for t in set(termes(champ or "")):
                    d = idx._champs.setdefault(t, {})
                    d[doc_i] = max(d.get(doc_i, 0.0), poids)
                    vus.add(t)
            pids = idx._par_doc.setdefault(doc_i, [])
            for msg in messages:
                if msg["texte"].startswith(MESSAGE_SANS_TEXTE):
                    continue
                for morceau in _decouper(msg["texte"]):
                    for mot in _MOT_RE.findall(morceau):
                        c = idx._casse.setdefault(_fold(mot), [0, 0])
                        c[mot[0].isupper()] += 1
                    ts = []
                    for mot in _TOKEN_RE.findall(_fold(morceau)):
                        if len(mot) < 2 or mot in STOPWORDS:
                            continue
                        r = memo.get(mot)
                        if r is None:
                            r = memo[mot] = racine(mot)
                            fam = famille(mot)
                            if fam:
                                idx._familles.setdefault(fam, set()).add(r)
                        ts.append(r)
                    if not ts:
                        continue
                    pid = len(idx.passages)
                    idx.passages.append((doc_i, msg["n"], msg["auteur"], morceau))
                    idx._plen.append(len(ts))
                    pids.append(pid)
                    compte = {}
                    for t in ts:
                        compte[t] = compte.get(t, 0) + 1
                    for t, tf in compte.items():
                        pl = idx._post.get(t)
                        if pl is None:
                            pl = idx._post[t] = (array("I"), array("B"))
                        pl[0].append(pid)
                        pl[1].append(min(tf, 255))
                    vus.update(compte)
            vus_par_doc.append(vus)
        for vus in vus_par_doc:
            for t in vus:
                idx._df_doc[t] = idx._df_doc.get(t, 0) + 1
        if idx._plen:
            idx._avgdl = sum(idx._plen) / len(idx._plen)
        return idx

    def __len__(self):
        return len(self.docs)

    @property
    def couverture(self):
        """Part des sujets dont le CONTENU est indexé (et pas seulement le titre)."""
        return sum(1 for d in self.docs if d["copie"]) / len(self.docs) if self.docs else 0.0

    def mot_courant(self, mot):
        """Vrai si ce mot (plié) est un mot de la langue et non un nom propre : dans les textes
        du forum, on le lit plus souvent SANS majuscule qu'avec. « Terre », « Ordre » dans un titre
        ne désignent alors aucune fiche en particulier ; « Tasglev », toujours capitalisé, si."""
        sans, avec = self._casse.get(mot, (0, 0))
        return sans >= 2 and sans > avec

    # -- vocabulaire : variantes et fautes de frappe -----------------------------------
    def _idf(self, t, n, df):
        return math.log(1.0 + (n - df + 0.5) / (df + 0.5))

    def _variantes(self, t, fam=""):
        """[(racine, poids)] : le terme lui-même, les mots de sa famille (fondé → fondation,
        fondateur), ses variantes de forme (Skaldia → Skaldien) et, s'il est inconnu du forum, la
        correction de faute de frappe la plus proche."""
        connu = t in self._df_doc
        out = {t: 1.0} if connu else {}
        for v in self._familles.get(fam, ()) if fam else ():
            out.setdefault(v, 0.45)
        if len(t) < 5 or t.isdigit():
            return list(out.items())
        if self._prefixes is None:
            self._prefixes = {}
            for v in self._df_doc:
                self._prefixes.setdefault(v[:3], []).append(v)
        tol = 2 if len(t) >= 8 else 1
        candidats = []
        for v in self._prefixes.get(t[:3], ()):
            if v == t or len(v) < 4:
                continue
            commun = len(os.path.commonprefix((t, v)))
            if commun >= max(5, min(len(t), len(v)) - 1) and abs(len(t) - len(v)) <= 3:
                candidats.append((0.5, v))                       # même nom, autre forme
            elif not connu and _distance(t, v, tol) <= tol:
                candidats.append((0.75, v))                      # faute de frappe
            elif connu and len(t) >= 6 and _distance(t, v, 1) <= 1:
                candidats.append((0.4, v))                       # deux graphies qui coexistent sur le forum
        if not connu and not candidats:
            for v in get_close_matches(t, self._df_doc.keys(), n=2, cutoff=0.82):
                candidats.append((0.7, v))
        # Les formes qui figurent dans un TITRE passent devant (ce sont des noms d'entités).
        candidats.sort(key=lambda c: (-c[0], -(1 if c[1] in self._champs else 0),
                                      -self._df_doc.get(c[1], 0)))
        for poids, v in candidats[:6]:
            out.setdefault(v, poids)
        return list(out.items())

    # -- recherche ---------------------------------------------------------------------
    def search(self, requete, limit=10, passages_par_doc=3, urls=None, appoint=""):
        """Résultats classés pour `requete`. `urls` restreint la recherche à ces sujets.
        `appoint` : des mots en plus (la question posée, en clair) qui aident à départager et à
        choisir les passages, mais pèsent peu et ne suffisent pas à retenir un sujet — seuls les
        mots de `requete` décident de ce qui est un résultat.
        Chaque résultat : {url, titre, chemin, maj, copie, n_posts, score, couverture,
        extrait, passages: [{n, auteur, texte, score}]}."""
        expressions = [_fold(e).strip() for e in re.findall(r'"([^"]{2,})"', requete or "")]
        expressions = [e for e in expressions if e]
        mots = [t for t in _TOKEN_RE.findall(_fold(requete or "")) if len(t) >= 2 and t not in STOPWORDS]
        if not mots:     # requête faite uniquement de mots vides : on les prend tels quels
            mots = [t for t in _TOKEN_RE.findall(_fold(requete or "")) if len(t) >= 3]
        familles = {}
        for t in mots:
            familles.setdefault(racine(t), famille(t))
        q = list(familles)
        if not q or not self.docs:
            return []
        n_prim = len(q)
        for t in _TOKEN_RE.findall(_fold(appoint or "")):
            if len(t) >= 2 and t not in STOPWORDS:
                familles.setdefault(racine(t), famille(t))
        q = list(familles)                                  # les mots de la requête, puis l'appoint
        poids_q = [1.0] * n_prim + [0.3] * (len(q) - n_prim)
        permis = None
        if urls is not None:
            permis = {i for i, d in enumerate(self.docs) if d["url"] in urls}
        variantes = [self._variantes(t, familles[t]) for t in q]
        n_pass, n_docs = max(1, len(self.passages)), len(self.docs)

        # 1) passages : BM25, le meilleur variant de chaque mot de la requête
        score_p, touche_p = {}, {}
        for qi, vs in enumerate(variantes):
            meilleur = {}
            for v, poids in vs:
                pl = self._post.get(v)
                if pl is None:
                    continue
                idf = self._idf(v, n_pass, len(pl[0]))
                for pid, tf in zip(pl[0], pl[1]):
                    s = poids_q[qi] * poids * idf * tf * (_BM25_K1 + 1) / (
                        tf + _BM25_K1 * (1 - _BM25_B + _BM25_B * self._plen[pid] / self._avgdl))
                    if s > meilleur.get(pid, 0.0):
                        meilleur[pid] = s
            for pid, s in meilleur.items():
                score_p[pid] = score_p.get(pid, 0.0) + s
                touche_p.setdefault(pid, set()).add(qi)

        # 2) affinage des meilleurs passages : expression exacte, mots voisins, message d'ouverture
        phrase = " ".join(_TOKEN_RE.findall(_fold(requete or ""))) if n_prim > 1 else ""
        formes = [{v for v, _ in vs} for vs in variantes]
        for pid in sorted(score_p, key=score_p.get, reverse=True)[:60]:
            _d, n_msg, _a, texte = self.passages[pid]
            plie = " ".join(_TOKEN_RE.findall(_fold(texte)))
            if phrase and phrase in plie:
                score_p[pid] *= 1.5
            elif len(q) > 1:
                suite = termes(texte)
                paires = sum(1 for a, b in zip(formes, formes[1:])
                             if any(x in a and y in b for x, y in zip(suite, suite[1:])))
                score_p[pid] *= 1.0 + 0.15 * paires
            if n_msg == 1:
                score_p[pid] *= 1.1            # la fiche elle-même prime sur les commentaires

        # 3) sujets : meilleurs passages + poids du titre / de la rubrique / des mots-clés
        par_doc = {}
        for pid, s in score_p.items():
            par_doc.setdefault(self.passages[pid][0], []).append((s, pid))
        score_d, touche_d = {}, {}
        for doc_i, lst in par_doc.items():
            lst.sort(reverse=True)
            score_d[doc_i] = sum(s * w for (s, _), w in zip(lst, (1.0, 0.4, 0.2)))
            touche_d[doc_i] = set().union(*(touche_p[pid] for _, pid in lst))
        for qi, vs in enumerate(variantes):
            meilleur = {}
            for v, poids in vs:
                idf = self._idf(v, n_docs, self._df_doc.get(v, 0))
                for doc_i, pc in self._champs.get(v, {}).items():
                    s = poids_q[qi] * poids * idf * pc
                    if s > meilleur.get(doc_i, 0.0):
                        meilleur[doc_i] = s
            for doc_i, s in meilleur.items():
                score_d[doc_i] = score_d.get(doc_i, 0.0) + s
                touche_d.setdefault(doc_i, set()).add(qi)

        resultats = []
        for doc_i, s in score_d.items():
            if permis is not None and doc_i not in permis:
                continue
            d = self.docs[doc_i]
            couverture = sum(1 for qi in touche_d[doc_i] if qi < n_prim) / n_prim
            if not couverture:
                continue                                   # aucun mot de la requête : hors sujet
            s *= 0.4 + 0.6 * couverture                    # un sujet qui a TOUS les mots prime
            if phrase and phrase in " ".join(_TOKEN_RE.findall(self._titre_plie[doc_i])):
                s *= 1.6                                   # l'expression cherchée EST le titre
            if expressions:
                textes = [self._titre_plie[doc_i]] + [_fold(self.passages[pid][3])
                                                      for pid in self._par_doc.get(doc_i, ())]
                if not all(any(e in t for t in textes) for e in expressions):
                    continue                               # "expression exacte" exigée, absente
            meilleurs = [(sc, pid) for sc, pid in par_doc.get(doc_i, [])][:passages_par_doc]
            passages = [{"n": self.passages[pid][1], "auteur": self.passages[pid][2],
                         "texte": self.passages[pid][3], "score": round(sc, 3)}
                        for sc, pid in meilleurs]
            if passages:
                apercu = extrait(passages[0]["texte"], formes)
            else:            # seul le titre (ou la rubrique) a répondu : on montre le début de la fiche
                debut = self._par_doc.get(doc_i) or ()
                apercu = extrait(self.passages[debut[0]][3], ()) if debut else ""
            resultats.append({**d, "score": round(s, 3), "couverture": round(couverture, 2),
                              "passages": passages, "extrait": apercu})
        resultats.sort(key=lambda r: -r["score"])
        return resultats[:limit]


def extrait(texte, formes, largeur=260):
    """Extrait d'environ `largeur` caractères centré sur l'endroit où le plus de mots de la
    requête se rejoignent — ce que montre un moteur de recherche sous chaque résultat.
    `formes` : liste d'ensembles de racines (une entrée par mot de la requête)."""
    texte = re.sub(r"\s+", " ", texte or "").strip()
    if len(texte) <= largeur:
        return texte
    plie = _fold(texte)                                   # même longueur que `texte`
    touches = []                                          # (position, n° du mot de la requête)
    for m in _TOKEN_RE.finditer(plie):
        r = racine(m.group())
        for qi, f in enumerate(formes):
            if r in f:
                touches.append((m.start(), qi))
                break
    if not touches:
        return texte[:largeur].rsplit(" ", 1)[0] + "…"
    meilleur, debut = (-1, 0), touches[0][0]
    for i, (pos, _) in enumerate(touches):                # fenêtre glissante sur les occurrences
        dans = {qi for p, qi in touches[i:] if p < pos + largeur}
        nb = sum(1 for p, _q in touches[i:] if p < pos + largeur)
        if (len(dans), nb) > meilleur:
            meilleur, debut = (len(dans), nb), pos
    a = max(0, debut - 40)
    b = min(len(texte), a + largeur)
    if a > 0:
        a = texte.find(" ", a) + 1 or a
    if b < len(texte):
        b = texte.rfind(" ", a, b) if texte.rfind(" ", a, b) > a else b
    return ("…" if a > 0 else "") + texte[a:b].strip() + ("…" if b < len(texte) else "")


# ============================================================
# 3. CHOISIR QUOI CITER dans un long sujet
# ============================================================
def meilleurs_passages(contenu, requete, budget):
    """Les passages d'un sujet qui répondent le mieux à `requete`, dans l'ORDRE du sujet,
    jusqu'à `budget` caractères. Chaque passage est précédé de son message d'origine.
    Renvoie (texte, nombre de passages retenus, nombre total de passages)."""
    idx = ForumIndex.build([{"url": "sujet", "titre": "", "contenu": contenu}])
    total = len(idx.passages)
    if not total:
        return "", 0, 0
    trouves = idx.search(requete, limit=1, passages_par_doc=total)
    classes = trouves[0]["passages"] if trouves else []
    ordre = {(p[1], p[3]): i for i, p in enumerate(idx.passages)}
    retenus, taille = [], 0
    for p in classes:
        cout = len(p["texte"]) + 60
        if retenus and taille + cout > budget:
            continue
        retenus.append(p)
        taille += cout
    retenus.sort(key=lambda p: ordre.get((p["n"], p["texte"]), 0))
    blocs, dernier = [], None
    for p in retenus:
        if p["n"] != dernier:
            blocs.append(f"[message {p['n']}" + (f", {p['auteur']}" if p["auteur"] else "") + "]")
            dernier = p["n"]
        blocs.append(p["texte"])
    return "\n".join(blocs), len(retenus), total
