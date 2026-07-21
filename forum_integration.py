# -*- coding: utf-8 -*-
"""
FORUM INTEGRATION — branche forum_platform sur Tenebris (bot.py)
================================================================
Trois choses, et trois seulement, à faire dans bot.py :

    from forum_integration import setup_forum
    forum_pf, register_forum_platform_routes = setup_forum(
        bot, llm_completion=llm_completion, is_maitre=is_mschap)

puis, dans _register_admin_routes(app) :

    register_forum_platform_routes(app, _is_authed, _auth_guard)

C'est tout : les commandes « ²T f… » et la page /plateforme existent.

Ce module fournit :
  • les commandes Discord (préfixe) : structure, sujets, réponses, modération,
    recherche, liens, index, droits par rôle ;
  • l'extracteur d'entités LLM (route « analyse » → Mistral) avec repli heuristique ;
  • la page web /plateforme : navigateur deux volets (arborescence + sujet),
    liens wiki cliquables, rétroliens, suggestions, graphe de connaissances,
    recherche avancée — même session que le panneau admin.
"""

import json
import asyncio
import discord
from aiohttp import web

from forum_platform import ForumPlatform, ENTITY_TYPES, ENTITY_LABELS

# ============================================================
# EXTRACTEUR D'ENTITÉS PAR LLM
# ============================================================
_EXTRACT_PROMPT = (
    "Tu extrais les entités d'un texte de forum de jeu de rôle. Réponds UNIQUEMENT "
    "avec un tableau JSON, sans autre texte ni balise Markdown. Chaque élément : "
    '{"type": "...", "nom": "..."} où type est parmi : personnage, lieu, evenement, '
    "organisation, objet, motcle. N'invente RIEN : uniquement ce qui est nommé dans "
    "le texte. Maximum 20 entités, les plus importantes d'abord."
)


def _make_llm_extractor(llm_completion):
    """Fabrique la coroutine texte → entités, posée sur la route « analyse »."""
    async def extract(texte):
        rep = await llm_completion(
            [{"role": "system", "content": _EXTRACT_PROMPT},
             {"role": "user", "content": (texte or "")[:6000]}],
            route="analyse", temperature=0.1, max_tokens=800)
        raw = rep if isinstance(rep, str) else str(rep)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        start, end = raw.find("["), raw.rfind("]")
        if start < 0 or end <= start:
            return []
        data = json.loads(raw[start:end + 1])
        return [e for e in data if isinstance(e, dict)
                and e.get("type") in ENTITY_TYPES and e.get("nom")]
    return extract


# ============================================================
# AIDE À L'AFFICHAGE DISCORD
# ============================================================
def _flags(t):
    out = []
    if t.get("epingle"):
        out.append("📌")
    if t.get("verrouille"):
        out.append("🔒")
    if t.get("archive"):
        out.append("📦")
    return " ".join(out)


def _chunk(text, size=1900):
    """Coupe un texte pour tenir dans les messages Discord."""
    parts, buf = [], ""
    for line in (text or "").split("\n"):
        if len(buf) + len(line) + 1 > size:
            parts.append(buf)
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        parts.append(buf)
    return parts or [""]


# ============================================================
# MISE EN PLACE
# ============================================================
def setup_forum(bot, llm_completion=None, is_maitre=None,
                forum_content_getter=None, library_getter=None):
    """Instancie la plateforme, enregistre les commandes Discord, et renvoie
    (forum, register_routes) — register_routes est à appeler avec l'app aiohttp.
    forum_content_getter / library_getter : les fonctions forum_content() et
    library() de bot.py, pour peupler la plateforme depuis la copie du forum
    externe (commande ²T fimport et bouton d'import de la page /forum)."""
    forum = ForumPlatform()
    if llm_completion:
        forum.set_llm_extractor(_make_llm_extractor(llm_completion))
    maitre = is_maitre or (lambda uid, name=None: False)

    # ---- droits -----------------------------------------------------------
    def _member_level(ctx_or_member, forum_id):
        m = getattr(ctx_or_member, "author", ctx_or_member)
        roles = [r.id for r in getattr(m, "roles", [])]
        return forum.level_for(forum_id, roles, is_owner=maitre(m.id, getattr(m, "name", "")))

    async def _need(ctx, forum_id, niveau, action):
        lvl = _member_level(ctx, forum_id)
        if lvl < niveau:
            besoin = {0: "lecture", 1: "écriture", 2: "modération"}[niveau]
            await ctx.send(f"Tes rôles ne te donnent pas le droit de {action} ici "
                           f"(niveau requis : {besoin}).")
            return False
        return True

    def _analyse_bg(topic_id, contenu):
        """Lance l'extraction LLM en tâche de fond, sans bloquer la réponse."""
        try:
            asyncio.get_running_loop().create_task(forum.analyze_post_async(topic_id, contenu))
        except RuntimeError:
            pass

    # ---- import des archives du forum externe -----------------------------
    async def import_archives():
        """Verse la copie interne du forum externe (forum_content + library)
        dans la plateforme : arborescence reconstruite depuis les fils d'Ariane,
        un sujet (verrouillé) par fiche, liens retissés, puis réindexation
        complète (entités + liens auto + wiki). Idempotent : relançable pour
        rattraper les fiches copiées depuis."""
        fc = (forum_content_getter() if forum_content_getter else {}) or {}
        lib = (library_getter() if library_getter else {}) or {}
        urls = list(dict.fromkeys(list(fc) + list(lib)))
        if not urls:
            return None

        def _run():
            mapping, liens_par_url = {}, {}
            stats = {"cree": 0, "maj": 0, "inchange": 0}
            for url in urls:
                e, le = fc.get(url, {}), lib.get(url, {})
                titre = e.get("titre") or le.get("titre") or ""
                chemin = le.get("chemin") or e.get("chemin") or ""
                contenu = (e.get("contenu") or "").strip()
                if not contenu:
                    # Fiche indexée mais pas encore copiée : on garde au moins le résumé,
                    # la relance d'un fimport ultérieur remplacera par le texte complet.
                    resume = (le.get("resume") or "").strip()
                    contenu = ("\U0001F4C4 (résumé seulement — la fiche n'a pas encore été "
                               "copiée par la veille)\n\n" + resume) if resume else ""
                tid, st = forum.import_external_topic(url, titre, chemin, contenu)
                stats[st] += 1
                mapping[url] = tid
                liens_par_url[url] = [l.get("url") for l in e.get("liens", []) if l.get("url")]
            stats["liens"] = forum.import_links(mapping, liens_par_url)
            stats["reindex"] = forum.reindex_all()
            return stats
        return await asyncio.to_thread(_run)

    # ======================================================================
    # COMMANDES DISCORD
    # ======================================================================
    @bot.command(name="fcat", help="Crée une catégorie du forum interne (modération) : ²T fcat Nom | description")
    async def fcat(ctx, *, args):
        if not maitre(ctx.author.id, ctx.author.name):
            return await ctx.send("Seul mon Maître façonne les catégories.")
        nom, _, desc = args.partition("|")
        cid = forum.create_category(nom.strip(), desc.strip())
        await ctx.send(f"🗂️ Catégorie **{nom.strip()}** créée (n°{cid}).")

    @bot.command(name="fforum", help="Crée un forum ou sous-forum : ²T fforum <n°catégorie> Nom | description | n°parent")
    async def fforum(ctx, categorie: int, *, args):
        if not maitre(ctx.author.id, ctx.author.name):
            return await ctx.send("Seul mon Maître façonne les forums.")
        parts = [p.strip() for p in args.split("|")]
        nom = parts[0]
        desc = parts[1] if len(parts) > 1 else ""
        parent = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
        try:
            fid = forum.create_forum(categorie, nom, desc, parent)
        except ValueError as e:
            return await ctx.send(f"Impossible : {e}.")
        genre = "Sous-forum" if parent else "Forum"
        await ctx.send(f"📁 {genre} **{nom}** créé (n°{fid}).")

    @bot.command(name="fdroits", help="Droits d'un forum par rôle : ²T fdroits <n°forum> @Rôle lecture|ecriture|moderation|aucun")
    async def fdroits(ctx, forum_id: int, role: discord.Role, niveau: str):
        if not maitre(ctx.author.id, ctx.author.name):
            return await ctx.send("Seul mon Maître distribue les droits.")
        table = {"lecture": 0, "ecriture": 1, "écriture": 1, "moderation": 2,
                 "modération": 2, "aucun": None}
        if niveau.lower() not in table:
            return await ctx.send("Niveau inconnu : lecture, ecriture, moderation ou aucun.")
        forum.set_permission(forum_id, role.id, table[niveau.lower()])
        await ctx.send(f"🔑 Rôle **{role.name}** → {niveau.lower()} sur le forum n°{forum_id}. "
                       "(Dès qu'un forum a UNE règle, seuls les rôles listés y accèdent.)")

    @bot.command(name="farbre", help="Arborescence du forum interne")
    async def farbre(ctx):
        cats = forum.tree()
        if not cats:
            return await ctx.send("Le forum est vide. Commence par `²T fcat Nom`.")
        lines = []
        for cat in cats:
            lines.append(f"🗂️ **{cat['nom']}** (n°{cat['id']})")
            def rec(f, depth=1):
                lines.append("　" * depth + f"📁 {f['nom']} (n°{f['id']}) — {f['nb_sujets']} sujet(s)")
                for sf in f["sous_forums"]:
                    rec(sf, depth + 1)
            for f in cat["forums"]:
                rec(f)
        for part in _chunk("\n".join(lines)):
            await ctx.send(part)

    @bot.command(name="fsujet", help="Nouveau sujet : ²T fsujet <n°forum> Titre | texte (les [[liens wiki]] marchent)")
    async def fsujet(ctx, forum_id: int, *, args):
        if not await _need(ctx, forum_id, 1, "ouvrir un sujet"):
            return
        titre, sep, texte = args.partition("|")
        if not sep or not texte.strip():
            return await ctx.send("Il me faut : `²T fsujet <n°forum> Titre | premier message`.")
        try:
            tid, warns = forum.create_topic(forum_id, titre.strip(), texte.strip(),
                                            ctx.author.id, ctx.author.display_name)
        except ValueError as e:
            return await ctx.send(f"Impossible : {e}.")
        _analyse_bg(tid, texte)
        msg = f"📝 Sujet **{titre.strip()}** ouvert (n°{tid})."
        if warns:
            doublons = ", ".join(f"« {w['titre']} » (n°{w['id']})" for w in warns[:3])
            msg += f"\n⚠️ Sujets très proches existants : {doublons}. Doublon ?"
        sugg = forum.related_topics(tid, limit=3)
        if sugg:
            msg += "\n🔗 Connexes : " + ", ".join(f"{s['titre']} (n°{s['id']})" for s in sugg)
        await ctx.send(msg)

    @bot.command(name="frep", help="Répond à un sujet : ²T frep <n°sujet> texte")
    async def frep(ctx, topic_id: int, *, texte):
        t = forum.get_topic(topic_id, with_posts=False, count_view=False)
        if not t:
            return await ctx.send("Sujet inconnu.")
        if not await _need(ctx, t["forum_id"], 1, "répondre"):
            return
        try:
            forum.reply(topic_id, texte, ctx.author.id, ctx.author.display_name)
        except PermissionError as e:
            return await ctx.send(f"Non : {e}.")
        _analyse_bg(topic_id, texte)
        await ctx.send(f"💬 Réponse ajoutée à **{t['titre']}**.")

    @bot.command(name="fsujets", help="Sujets d'un forum : ²T fsujets <n°forum> [page]")
    async def fsujets(ctx, forum_id: int, page: int = 1):
        if not await _need(ctx, forum_id, 0, "lire"):
            return
        rows = forum.list_topics(forum_id, page=page)
        if not rows:
            return await ctx.send("Aucun sujet ici (ou page vide).")
        lines = [f"{_flags(t)} **{t['titre']}** (n°{t['id']}) — {t['nb_posts']} msg, "
                 f"maj {t['maj_le'][:16]}" for t in rows]
        for part in _chunk("\n".join(lines)):
            await ctx.send(part)

    @bot.command(name="flire", help="Lit un sujet : ²T flire <n°sujet> [page]")
    async def flire(ctx, topic_id: int, page: int = 1):
        t = forum.get_topic(topic_id)
        if not t:
            return await ctx.send("Sujet inconnu.")
        if not await _need(ctx, t["forum_id"], 0, "lire"):
            return
        per, posts = 4, t["posts"]
        total = max(1, (len(posts) + per - 1) // per)
        page = min(max(1, page), total)
        chunk = posts[(page - 1) * per: page * per]
        head = (f"{_flags(t)} **{t['titre']}** (n°{topic_id})\n"
                f"🧭 {' › '.join(t['chemin'])}\n"
                f"👁️ {t['vues']} vues — page {page}/{total}\n" + "─" * 30)
        corps = [head]
        for p in chunk:
            corps.append(f"**{p['auteur_nom']}** · {p['cree_le'][:16]}\n{p['contenu']}")
        liens = forum.links_of(topic_id)
        if liens:
            corps.append("🔗 **Liés** : " + ", ".join(
                f"{l['titre']} (n°{l['id']}){'↩' if l['retour'] else ''}" for l in liens[:8]))
        sugg = forum.related_topics(topic_id, limit=4)
        if sugg:
            corps.append("💡 **Connexes** : " + ", ".join(
                f"{s['titre']} (n°{s['id']})" for s in sugg))
        for part in _chunk("\n\n".join(corps)):
            await ctx.send(part)

    @bot.command(name="fchercher", help="Recherche : ²T fchercher mots ou personnage:Nom lieu:Nom avec:\"Titre\"")
    async def fchercher(ctx, *, requete):
        hits = forum.search(requete)
        if not hits:
            return await ctx.send("Rien trouvé — ni dans les titres, ni dans les messages, "
                                  "ni dans le graphe.")
        lines = [f"🔎 **Résultats pour** `{requete}` :"]
        for h in hits[:15]:
            lines.append(f"• **{h['titre']}** (n°{h['id']}) — {h['chemin']} · score {h['score']}")
        await ctx.send("\n".join(lines)[:1990])

    @bot.command(name="findex", help="Index par thème (entités) : ²T findex [type]")
    async def findex(ctx, type_: str = ""):
        idx = forum.theme_index()
        if type_ and type_.lower() in ENTITY_TYPES:
            idx = [e for e in idx if e["type"] == type_.lower()]
        if not idx:
            return await ctx.send("Index vide pour l'instant : il se peuple au fil des messages.")
        lines = [f"📇 **Index** ({len(idx)} entrées) :"]
        for e in idx[:30]:
            lines.append(f"• [{ENTITY_LABELS[e['type']]}] **{e['nom']}** — {e['nb']} sujet(s)")
        for part in _chunk("\n".join(lines)):
            await ctx.send(part)

    @bot.command(name="fentites", help="Entités d'un sujet : ²T fentites <n°sujet>")
    async def fentites(ctx, topic_id: int):
        ents = forum.entities_of(topic_id)
        if not ents:
            return await ctx.send("Aucune entité indexée sur ce sujet (encore).")
        lines = [f"• [{ENTITY_LABELS.get(e['type'], e['type'])}] **{e['nom']}** ×{e['nb']}"
                 for e in ents[:25]]
        await ctx.send("\n".join(lines)[:1990])

    @bot.command(name="flier", help="Lie deux sujets : ²T flier <n°source> <n°cible> — retire avec « retirer » en 3e mot")
    async def flier(ctx, source: int, cible: int, action: str = ""):
        t = forum.get_topic(source, with_posts=False, count_view=False)
        if not t:
            return await ctx.send("Sujet source inconnu.")
        if not await _need(ctx, t["forum_id"], 1, "lier"):
            return
        if action.lower() in ("retirer", "supprimer", "off"):
            forum.remove_link(source, cible)
            return await ctx.send("🔗 Lien retiré (dans les deux sens).")
        if forum.add_link(source, cible):
            await ctx.send("🔗 Lien bidirectionnel créé.")
        else:
            await ctx.send("Cible inconnue, ou source = cible.")

    @bot.command(name="fverrou", help="Verrouille/déverrouille : ²T fverrou <n°sujet>")
    async def fverrou(ctx, topic_id: int):
        t = forum.get_topic(topic_id, with_posts=False, count_view=False)
        if not t or not await _need(ctx, t["forum_id"], 2, "verrouiller"):
            return
        forum.set_flag(topic_id, verrouille=not t["verrouille"])
        await ctx.send("🔒 Verrouillé." if not t["verrouille"] else "🔓 Déverrouillé.")

    @bot.command(name="fepingle", help="Épingle/désépingle : ²T fepingle <n°sujet>")
    async def fepingle(ctx, topic_id: int):
        t = forum.get_topic(topic_id, with_posts=False, count_view=False)
        if not t or not await _need(ctx, t["forum_id"], 2, "épingler"):
            return
        forum.set_flag(topic_id, epingle=not t["epingle"])
        await ctx.send("📌 Épinglé." if not t["epingle"] else "Désépinglé.")

    @bot.command(name="farchive", help="Archive/désarchive : ²T farchive <n°sujet>")
    async def farchive(ctx, topic_id: int):
        t = forum.get_topic(topic_id, with_posts=False, count_view=False)
        if not t or not await _need(ctx, t["forum_id"], 2, "archiver"):
            return
        forum.set_flag(topic_id, archive=not t["archive"])
        await ctx.send("📦 Archivé." if not t["archive"] else "Sorti des archives.")

    @bot.command(name="fdeplacer", help="Déplace un sujet : ²T fdeplacer <n°sujet> <n°forum>")
    async def fdeplacer(ctx, topic_id: int, forum_id: int):
        t = forum.get_topic(topic_id, with_posts=False, count_view=False)
        if not t or not await _need(ctx, t["forum_id"], 2, "déplacer"):
            return
        forum.move_topic(topic_id, forum_id)
        await ctx.send(f"📦 Sujet n°{topic_id} déplacé vers le forum n°{forum_id}.")

    @bot.command(name="fimport", help="Verse les archives du forum externe dans la plateforme (Maître)")
    async def fimport(ctx):
        if not maitre(ctx.author.id, ctx.author.name):
            return await ctx.send("Seul mon Maître déclenche ce déversement.")
        await ctx.send("\u23F3 Import des archives en cours — arborescence, sujets, "
                       "liens, puis réindexation. Ça peut prendre un moment…")
        async with ctx.typing():
            stats = await import_archives()
        if stats is None:
            return await ctx.send("La copie du forum externe est vide : lance d'abord "
                                  "la veille (bibliothèque) pour qu'elle archive des fiches.")
        await ctx.send(
            f"\U0001F4E6 **Import terminé** — {stats['cree']} sujet(s) créé(s), "
            f"{stats['maj']} mis à jour, {stats['inchange']} inchangé(s), "
            f"{stats['liens']} lien(s) retissé(s), {stats['reindex']} sujet(s) réindexé(s). "
            f"Tout est sur /forum.")

    @bot.command(name="fstats", help="Statistiques du forum interne")
    async def fstats(ctx):
        s = forum.stats()
        await ctx.send(
            f"📊 **Forum interne** — {s['categories']} catégorie(s), {s['forums']} forum(s), "
            f"{s['sujets']} sujet(s), {s['messages']} message(s), {s['entites']} entité(s), "
            f"{s['liens']} lien(s). Recherche : {'FTS5' if s['fts'] else 'LIKE'}.")

    @bot.command(name="freindex", help="Reconstruit l'index et les liens auto (Maître uniquement)")
    async def freindex(ctx):
        if not maitre(ctx.author.id, ctx.author.name):
            return await ctx.send("Seul mon Maître relance l'indexation.")
        async with ctx.typing():
            n = await asyncio.to_thread(forum.reindex_all)
        await ctx.send(f"🧮 Réindexation terminée : {n} sujet(s) repassés au crible.")

    # ======================================================================
    # ROUTES WEB — /plateforme (même session que le panneau admin)
    # ======================================================================
    async def _read_json(request):
        try:
            return await request.json()
        except Exception:
            return {}

    def register_routes(app, is_authed, auth_guard):
        async def page(request):
            if not is_authed(request):
                raise web.HTTPFound("/admin")
            return web.Response(text=PLATFORM_HTML, content_type="text/html")

        async def api(request):
            guard = auth_guard(request)
            if guard:
                return guard
            if request.method == "POST":
                data = await _read_json(request)
                act = data.get("action")
                try:
                    if act == "topic_new":
                        tid, warns = forum.create_topic(
                            int(data["forum_id"]), data.get("titre", ""),
                            data.get("contenu", ""), "panel", data.get("auteur") or "Panneau")
                        _analyse_bg(tid, data.get("contenu", ""))
                        return web.json_response({"ok": True, "id": tid, "doublons": warns})
                    if act == "reply":
                        forum.reply(int(data["topic_id"]), data.get("contenu", ""),
                                    "panel", data.get("auteur") or "Panneau")
                        _analyse_bg(int(data["topic_id"]), data.get("contenu", ""))
                        return web.json_response({"ok": True})
                    if act == "flag":
                        forum.set_flag(int(data["topic_id"]),
                                       verrouille=data.get("verrouille"),
                                       epingle=data.get("epingle"),
                                       archive=data.get("archive"))
                        return web.json_response({"ok": True})
                    if act == "link_add":
                        ok = forum.add_link(int(data["source"]), int(data["cible"]))
                        return web.json_response({"ok": ok})
                    if act == "link_remove":
                        forum.remove_link(int(data["source"]), int(data["cible"]))
                        return web.json_response({"ok": True})
                    if act == "cat_new":
                        cid = forum.create_category(data.get("nom", ""), data.get("description", ""))
                        return web.json_response({"ok": True, "id": cid})
                    if act == "import":
                        stats = await import_archives()
                        if stats is None:
                            return web.json_response(
                                {"ok": False, "error": "copie du forum externe vide"}, status=400)
                        return web.json_response({"ok": True, **stats})
                    if act == "forum_new":
                        fid = forum.create_forum(int(data["categorie_id"]), data.get("nom", ""),
                                                 data.get("description", ""),
                                                 int(data["parent_id"]) if data.get("parent_id") else None)
                        return web.json_response({"ok": True, "id": fid})
                except (ValueError, PermissionError, KeyError) as e:
                    return web.json_response({"ok": False, "error": str(e)}, status=400)
                return web.json_response({"error": "action inconnue"}, status=400)

            act = request.query.get("action", "tree")
            if act == "tree":
                return web.json_response({"tree": forum.tree(), "stats": forum.stats()})
            if act == "topics":
                fid = int(request.query.get("forum", 0))
                page_n = int(request.query.get("page", 1))
                return web.json_response({"topics": forum.list_topics(fid, page=page_n)})
            if act == "topic":
                tid = int(request.query.get("id", 0))
                t = forum.get_topic(tid)
                if not t:
                    return web.json_response({"error": "sujet inconnu"}, status=404)
                for p in t["posts"]:
                    p["html"] = forum.autolink_html(tid, p["contenu"], url_base="/forum")
                t["liens"] = forum.links_of(tid)
                t["entites"] = forum.entities_of(tid)
                t["suggestions"] = forum.related_topics(tid)
                t["doublons"] = forum.find_duplicates(t["titre"], exclude_id=tid)
                return web.json_response(t)
            if act == "search":
                return web.json_response({"hits": forum.search(request.query.get("q", ""))})
            if act == "index":
                return web.json_response({"index": forum.theme_index()})
            if act == "entity":
                eid = int(request.query.get("id", 0))
                return web.json_response({"topics": forum.topics_of_entity(eid)})
            if act == "graph":
                tid = request.query.get("topic")
                return web.json_response(forum.graph(int(tid) if tid else None))
            if act == "export":
                return web.Response(text=forum.export_json(), content_type="application/json")
            return web.json_response({"error": "action inconnue"}, status=400)

        app.router.add_get("/forum", page)               # LA page forum du bot
        app.router.add_get("/forum/", page)
        app.router.add_get("/plateforme", page)          # alias conservé
        app.router.add_get("/plateforme/", page)
        app.router.add_get("/admin/api/plateforme", api)
        app.router.add_post("/admin/api/plateforme", api)

    return forum, register_routes


# ============================================================
# PAGE WEB /plateforme — navigateur deux volets, thème sombre
# ============================================================
PLATFORM_HTML = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tenebris — Plateforme</title>
<style>
:root{--bg:#0d0f14;--panel:#151823;--panel2:#1b1f2e;--tx:#c9cede;--dim:#7d8296;
--acc:#8b5cf6;--acc2:#a78bfa;--ok:#34d399;--warn:#fbbf24;--bad:#f87171;--line:#262b3d}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--tx);font:14px/1.55 'Segoe UI',system-ui,sans-serif;height:100vh;display:flex;flex-direction:column}
header{display:flex;gap:10px;align-items:center;padding:10px 16px;background:var(--panel);border-bottom:1px solid var(--line)}
header h1{font-size:16px;color:var(--acc2);letter-spacing:.5px}
header input{flex:1;max-width:520px;background:var(--panel2);border:1px solid var(--line);color:var(--tx);border-radius:8px;padding:7px 12px;outline:none}
header input:focus{border-color:var(--acc)}
header a{color:var(--dim);text-decoration:none;font-size:12px}
main{flex:1;display:flex;min-height:0}
#tree{width:320px;min-width:240px;overflow:auto;background:var(--panel);border-right:1px solid var(--line);padding:12px}
#view{flex:1;overflow:auto;padding:18px 24px}
.cat{margin-bottom:14px}.cat>h3{color:var(--acc2);font-size:13px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.forum{padding:5px 8px;border-radius:6px;cursor:pointer;color:var(--tx)}
.forum:hover{background:var(--panel2)}
.forum .n{color:var(--dim);font-size:12px}
.sub{margin-left:16px;border-left:1px solid var(--line);padding-left:6px}
.topic-row{padding:7px 10px;border-radius:6px;cursor:pointer;display:flex;gap:8px;align-items:baseline}
.topic-row:hover{background:var(--panel2)}
.topic-row .meta{color:var(--dim);font-size:12px;margin-left:auto;white-space:nowrap}
.crumb{color:var(--dim);font-size:12px;margin-bottom:8px}
.crumb b{color:var(--tx)}
h2.title{font-size:20px;color:#fff;margin-bottom:4px}
.badge{display:inline-block;font-size:11px;border:1px solid var(--line);border-radius:10px;padding:1px 8px;margin-right:5px;color:var(--dim)}
.badge.on{color:var(--warn);border-color:var(--warn)}
.post{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:12px 0}
.post .who{color:var(--acc2);font-weight:600;font-size:13px}
.post .when{color:var(--dim);font-size:11px;margin-left:8px}
.post .body{margin-top:8px;white-space:pre-wrap}
a.wikilink{color:var(--acc2);text-decoration:none;border-bottom:1px dotted var(--acc2)}
a.wikilink.auto{border-bottom-style:dashed;opacity:.9}
.wikilink.missing{color:var(--bad);border-bottom:1px dotted var(--bad)}
.side{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px}
.card h4{font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.chip{display:inline-block;background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:2px 10px;margin:2px;font-size:12px;cursor:pointer}
.chip:hover{border-color:var(--acc)}
.chip .t{color:var(--dim);font-size:10px;margin-right:4px;text-transform:uppercase}
.list a{display:block;color:var(--tx);text-decoration:none;padding:3px 0;font-size:13px}
.list a:hover{color:var(--acc2)}
.btn{background:var(--panel2);border:1px solid var(--line);color:var(--tx);border-radius:7px;padding:6px 12px;cursor:pointer;font-size:13px}
.btn:hover{border-color:var(--acc)}
.btn.warn{color:var(--warn)}
textarea,input.f{width:100%;background:var(--panel2);border:1px solid var(--line);color:var(--tx);border-radius:8px;padding:8px 10px;margin:5px 0;outline:none;font:inherit}
textarea{min-height:90px;resize:vertical}
#graph{width:100%;height:280px;background:var(--panel2);border-radius:8px}
.dim{color:var(--dim);font-size:12px}
.warnbox{border:1px solid var(--warn);color:var(--warn);border-radius:8px;padding:8px 12px;margin:8px 0;font-size:13px}
.tools{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap}
</style></head><body>
<header>
  <h1>⚑ Plateforme</h1>
  <input id="q" placeholder="Rechercher — mots, personnage:Nom, lieu:Nom, avec:&quot;Titre lié&quot;…">
  <a href="/admin">← panneau</a><a href="/archives">📚 archives</a><a href="#" id="idxBtn">📇 index</a><a href="#" id="graphBtn">🕸 graphe</a>
</header>
<main>
  <div id="tree"></div>
  <div id="view"><p class="dim">Choisis un forum à gauche, ou cherche en haut. Les [[liens wiki]]
  et les titres cités deviennent cliquables dans les sujets.</p></div>
</main>
<script>
const api = (p) => fetch('/admin/api/plateforme'+p).then(r=>r.json());
const post = (b) => fetch('/admin/api/plateforme',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(r=>r.json());
const esc = s => (s||'').replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const V = document.getElementById('view');
let TREE = [];

function loadTree(){ api('?action=tree').then(d=>{ TREE = d.tree||[];
  const box = document.getElementById('tree'); box.innerHTML='';
  const s = d.stats||{};
  box.insertAdjacentHTML('beforeend', `<div class="dim" style="margin-bottom:10px">${s.sujets||0} sujets · ${s.messages||0} messages · ${s.entites||0} entités · ${s.liens||0} liens</div>`);
  TREE.forEach(cat=>{
    const c = document.createElement('div'); c.className='cat';
    c.innerHTML = `<h3>${esc(cat.nom)}</h3>`;
    const rec = (f, parent)=>{
      const el = document.createElement('div');
      el.className='forum'; el.innerHTML = `📁 ${esc(f.nom)} <span class="n">· ${f.nb_sujets}</span>`;
      el.onclick = ()=>openForum(f);
      parent.appendChild(el);
      if(f.sous_forums.length){ const sub=document.createElement('div'); sub.className='sub';
        f.sous_forums.forEach(sf=>rec(sf, sub)); parent.appendChild(sub); }
    };
    cat.forums.forEach(f=>rec(f, c));
    box.appendChild(c);
  });
  box.insertAdjacentHTML('beforeend', `<button class="btn" id="catNew">+ catégorie</button> <button class="btn" id="forNew">+ forum</button> <button class="btn" id="impBtn">\u21EA importer les archives</button>`);
  document.getElementById('catNew').onclick = ()=>{ const n=prompt('Nom de la catégorie ?'); if(n) post({action:'cat_new',nom:n}).then(loadTree); };
  document.getElementById('forNew').onclick = ()=>{ const c=prompt('N° de catégorie ?'), n=prompt('Nom du forum ?'), p=prompt('N° du forum parent (vide si aucun) ?');
    if(c&&n) post({action:'forum_new',categorie_id:c,nom:n,parent_id:p||null}).then(r=>{ if(r.error) alert(r.error); loadTree(); }); };
  document.getElementById('impBtn').onclick = ()=>{
    if(!confirm('Verser les archives du forum externe dans la plateforme ? (relançable sans doublon)')) return;
    const btn=document.getElementById('impBtn'); btn.textContent='\u23F3 import en cours…'; btn.disabled=true;
    post({action:'import'}).then(r=>{ btn.disabled=false; btn.textContent='\u21EA importer les archives';
      if(r.error) return alert(r.error);
      alert(`Import terminé : ${r.cree} créés, ${r.maj} mis à jour, ${r.inchange} inchangés, ${r.liens} liens, ${r.reindex} réindexés.`);
      loadTree(); }); };
});}

function openForum(f){ api('?action=topics&forum='+f.id).then(d=>{
  V.innerHTML = `<h2 class="title">📁 ${esc(f.nom)}</h2><p class="dim">${esc(f.description||'')}</p>
    <div class="tools"><button class="btn" id="tNew">+ nouveau sujet</button></div><div id="rows"></div>`;
  const rows = document.getElementById('rows');
  (d.topics||[]).forEach(t=>{
    const flags = (t.epingle?'📌':'')+(t.verrouille?'🔒':'')+(t.archive?'📦':'');
    const el = document.createElement('div'); el.className='topic-row';
    el.innerHTML = `<span>${flags} <b>${esc(t.titre)}</b></span><span class="meta">${t.nb_posts} msg · ${t.maj_le.slice(0,16)}</span>`;
    el.onclick = ()=>openTopic(t.id); rows.appendChild(el);
  });
  if(!(d.topics||[]).length) rows.innerHTML='<p class="dim">Aucun sujet.</p>';
  document.getElementById('tNew').onclick = ()=>{
    V.insertAdjacentHTML('beforeend', `<div class="card"><h4>Nouveau sujet</h4>
      <input class="f" id="nT" placeholder="Titre"><textarea id="nC" placeholder="Premier message — [[liens wiki]] autorisés"></textarea>
      <button class="btn" id="nGo">Publier</button></div>`);
    document.getElementById('nGo').onclick = ()=>post({action:'topic_new',forum_id:f.id,
      titre:document.getElementById('nT').value, contenu:document.getElementById('nC').value})
      .then(r=>{ if(r.error) return alert(r.error);
        if((r.doublons||[]).length) alert('⚠️ Sujets très proches : '+r.doublons.map(x=>x.titre).join(', '));
        openTopic(r.id); });
  };
});}

function openTopic(id){ api('?action=topic&id='+id).then(t=>{
  if(t.error) return alert(t.error);
  location.hash = 't'+id;
  const badges = `<span class="badge ${t.epingle?'on':''}">📌 épinglé</span>
    <span class="badge ${t.verrouille?'on':''}">🔒 verrouillé</span>
    <span class="badge ${t.archive?'on':''}">📦 archivé</span>`;
  V.innerHTML = `<div class="crumb">${t.chemin.slice(0,-1).map(esc).join(' › ')} › <b>${esc(t.titre)}</b></div>
    <h2 class="title">${esc(t.titre)}</h2><div>${badges} <span class="dim">👁 ${t.vues} vues · réf ${t.ref}</span></div>
    ${(t.doublons||[]).length?`<div class="warnbox">⚠️ Doublon possible : ${t.doublons.map(d=>`<a class="wikilink" href="#" onclick="openTopic(${d.id});return false">${esc(d.titre)}</a>`).join(', ')}</div>`:''}
    <div class="tools">
      <button class="btn warn" onclick="flag(${id},'epingle',${t.epingle?0:1})">📌 ${t.epingle?'désépingler':'épingler'}</button>
      <button class="btn warn" onclick="flag(${id},'verrouille',${t.verrouille?0:1})">🔒 ${t.verrouille?'déverrouiller':'verrouiller'}</button>
      <button class="btn warn" onclick="flag(${id},'archive',${t.archive?0:1})">📦 ${t.archive?'désarchiver':'archiver'}</button>
      <button class="btn" onclick="askLink(${id})">🔗 lier…</button>
    </div>
    <div id="posts"></div>
    ${t.verrouille||t.archive?'<p class="dim">Sujet fermé aux réponses.</p>':
      `<div class="card"><h4>Répondre</h4><textarea id="rC"></textarea><button class="btn" id="rGo">Envoyer</button></div>`}
    <div class="side">
      <div class="card"><h4>🔗 Sujets liés</h4><div class="list" id="lLinks"></div></div>
      <div class="card"><h4>💡 Suggestions connexes</h4><div class="list" id="lSugg"></div></div>
      <div class="card"><h4>🏷 Entités du sujet</h4><div id="lEnts"></div></div>
      <div class="card"><h4>🕸 Voisinage</h4><canvas id="graph"></canvas></div>
    </div>`;
  const P = document.getElementById('posts');
  (t.posts||[]).forEach(p=>{
    P.insertAdjacentHTML('beforeend', `<div class="post"><span class="who">${esc(p.auteur_nom)}</span>
      <span class="when">${p.cree_le}${p.modifie_le?' (modifié)':''}</span><div class="body">${p.html}</div></div>`);
  });
  P.querySelectorAll('a.wikilink[data-topic]').forEach(a=>a.onclick=e=>{e.preventDefault();openTopic(+a.dataset.topic);});
  const L = document.getElementById('lLinks');
  L.innerHTML = (t.liens||[]).map(l=>`<a href="#" onclick="openTopic(${l.id});return false">${l.retour?'↩ ':''}${esc(l.titre)} <span class="dim">(${l.type})</span></a>`).join('') || '<span class="dim">aucun</span>';
  const S = document.getElementById('lSugg');
  S.innerHTML = (t.suggestions||[]).map(s=>`<a href="#" onclick="openTopic(${s.id});return false">${esc(s.titre)} <span class="dim">· ${s.score}</span></a>`).join('') || '<span class="dim">rien à suggérer</span>';
  const E = document.getElementById('lEnts');
  E.innerHTML = (t.entites||[]).map(e=>`<span class="chip" data-eid="${e.id}" data-nom="${esc(e.nom)}"><span class="t">${e.type}</span>${esc(e.nom)} ×${e.nb}</span>`).join('') || '<span class="dim">rien d\u2019indexé</span>';
  E.querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>openEntity(+ch.dataset.eid, ch.dataset.nom));
  const go = document.getElementById('rGo');
  if(go) go.onclick = ()=>post({action:'reply',topic_id:id,contenu:document.getElementById('rC').value})
    .then(r=>r.error?alert(r.error):openTopic(id));
  drawGraph(id);
});}

function flag(id, k, v){ const b={action:'flag',topic_id:id}; b[k]=v; post(b).then(()=>openTopic(id)); }
function askLink(id){ const c = prompt('N° du sujet à lier ?'); if(c) post({action:'link_add',source:id,cible:+c}).then(()=>openTopic(id)); }
function openEntity(id, nom){ api('?action=entity&id='+id).then(d=>{
  V.innerHTML = `<h2 class="title">🏷 ${esc(nom)}</h2><p class="dim">Sujets citant cette entité :</p><div class="list" id="rows"></div>`;
  document.getElementById('rows').innerHTML = (d.topics||[]).map(t=>`<a href="#" onclick="openTopic(${t.id});return false">${esc(t.titre)} <span class="dim">×${t.nb}</span></a>`).join('');
});}

document.getElementById('q').addEventListener('keydown', e=>{
  if(e.key!=='Enter') return;
  api('?action=search&q='+encodeURIComponent(e.target.value)).then(d=>{
    V.innerHTML = `<h2 class="title">🔎 Résultats</h2><div class="list" id="rows"></div>`;
    document.getElementById('rows').innerHTML = (d.hits||[]).map(h=>
      `<a href="#" onclick="openTopic(${h.id});return false">${esc(h.titre)} <span class="dim">— ${esc(h.chemin)} · ${h.score}</span></a>`).join('') || '<p class="dim">Rien trouvé.</p>';
  });
});
document.getElementById('idxBtn').onclick = e=>{ e.preventDefault();
  api('?action=index').then(d=>{
    V.innerHTML = `<h2 class="title">📇 Index par thème</h2><div id="rows"></div>`;
    const R = document.getElementById('rows');
    R.innerHTML = (d.index||[]).map(x=>
      `<span class="chip" data-eid="${x.id}" data-nom="${esc(x.nom)}"><span class="t">${x.type}</span>${esc(x.nom)} · ${x.nb}</span>`).join('');
    R.querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>openEntity(+ch.dataset.eid, ch.dataset.nom));
  });};
document.getElementById('graphBtn').onclick = e=>{ e.preventDefault();
  V.innerHTML = `<h2 class="title">🕸 Graphe de connaissances</h2><canvas id="graph" style="height:75vh"></canvas>`;
  drawGraph(null); };

// --- mini graphe force-directed (sans dépendance) ------------------------
function drawGraph(topicId){
  api('?action=graph'+(topicId?'&topic='+topicId:'')).then(g=>{
    const cv = document.getElementById('graph'); if(!cv) return;
    const ctx = cv.getContext('2d');
    cv.width = cv.clientWidth; cv.height = cv.clientHeight || 280;
    const W=cv.width, H=cv.height;
    const nodes = g.nodes.map((n,i)=>({...n, x:W/2+Math.cos(i)*W/3*Math.random(), y:H/2+Math.sin(i)*H/3*Math.random(), vx:0, vy:0}));
    const byId = Object.fromEntries(nodes.map(n=>[n.id,n]));
    const edges = g.edges.filter(e=>byId[e.a]&&byId[e.b]);
    for(let it=0; it<160; it++){
      nodes.forEach(a=>{ nodes.forEach(b=>{ if(a===b) return;
        let dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy+0.01, f=1400/d2;
        a.vx+=dx*f/Math.sqrt(d2); a.vy+=dy*f/Math.sqrt(d2); });});
      edges.forEach(e=>{ const a=byId[e.a], b=byId[e.b];
        let dx=b.x-a.x, dy=b.y-a.y, d=Math.sqrt(dx*dx+dy*dy)+0.01, f=(d-90)*0.01;
        a.vx+=dx/d*f; a.vy+=dy/d*f; b.vx-=dx/d*f; b.vy-=dy/d*f; });
      nodes.forEach(n=>{ n.x=Math.max(20,Math.min(W-20,n.x+n.vx)); n.y=Math.max(14,Math.min(H-14,n.y+n.vy)); n.vx*=0.5; n.vy*=0.5; });
    }
    ctx.clearRect(0,0,W,H);
    ctx.strokeStyle='#2b3050';
    edges.forEach(e=>{ const a=byId[e.a], b=byId[e.b];
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); });
    nodes.forEach(n=>{
      const sujet = n.kind==='sujet';
      ctx.fillStyle = sujet ? '#8b5cf6' : '#34d399';
      ctx.beginPath(); ctx.arc(n.x,n.y, sujet?6:4, 0, 7); ctx.fill();
      ctx.fillStyle='#c9cede'; ctx.font='10px sans-serif';
      ctx.fillText(n.label.slice(0,22), n.x+8, n.y+3);
    });
    cv.onclick = ev=>{
      const r = cv.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;
      const hit = nodes.find(n=>(n.x-mx)**2+(n.y-my)**2<100);
      if(hit && hit.kind==='sujet') openTopic(hit.tid);
    };
  });
}

loadTree();
if(location.hash.startsWith('#t')) openTopic(+location.hash.slice(2));
</script></body></html>"""