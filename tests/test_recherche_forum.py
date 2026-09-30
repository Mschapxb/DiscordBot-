"""La recherche sur le forum, de bout en bout et hors ligne : lire un sujet en entier (toutes ses
pages, toutes ses réponses), chercher dans le texte complet, et ne jamais perdre la suite d'un
long sujet. Le réseau est remplacé par de fausses pages ; le modèle d'analyse par un faux."""
import unittest
from unittest import mock

import forum_engine as E
from support import load_bot

B = load_bot()

FORUM = "https://orbis-naturae.forumactif.com"


def page(messages, suivant=None, titre="Les Linnorms"):
    """Une page de sujet au format du forum : messages = [(id, auteur, date, html)]."""
    corps = "".join(
        f'<div id="post-{pid}" class="post-wrap post--{pid}"><div class="post-header">'
        f'<span class="post-date">{date}</span></div><div class="post-body"><div class="post-content">'
        f'{html}</div></div><aside><span class="post-author-name">{auteur}</span></aside></div>'
        for pid, auteur, date, html in messages)
    nav = f'<a rel="next" href="{suivant}">Suivant</a>' if suivant else ""
    return (f"<html><head><title>{titre}</title></head><body><div id='breadcrumbs'>"
            f'<a href="/c1-le-monde" class="nav"><span>Le monde d\'Orbis</span></a> :: '
            f'<a href="/f4-creatures" class="nav"><span>Créatures</span></a></div>{corps}{nav}</body></html>')


SUJET = f"{FORUM}/t3-les-linnorms"
PAGES = {
    SUJET: page([(29, "Rol-Vunshi", "Ven 19 Fév 2021", "Les Linnorms sont des dragons sans ailes."),
                 (30, "Mulos", "Sam 20 Fév 2021", 'Leur roi est Fafnir, voir <a href="/t7-le-col-de-givre">le Col</a>.')],
                suivant="/t3p15-les-linnorms"),
    f"{FORUM}/t3p15-les-linnorms": page(
        [(30, "Mulos", "Sam 20 Fév 2021", "doublon de bas de page"),
         (31, "Rol-Vunshi", "Dim 21 Fév 2021", "Dernière réponse : Fafnir dort sous le glacier.")]),
}


class Reseau:
    """Remplace _fetch_raw : sert les fausses pages et note ce qui a été demandé."""

    def __init__(self, pages):
        self.pages, self.demandes = dict(pages), []

    async def __call__(self, url, session=None):
        self.demandes.append(url)
        if url in self.pages:
            return {"url": url, "html": self.pages[url]}
        return {"url": url, "error": "HTTP 404"}


class HorsLigne(unittest.IsolatedAsyncioTestCase):
    """Base : une bibliothèque et une copie du forum vides, un faux réseau, pas de modèle."""
    pages = PAGES

    def setUp(self):
        self.reseau = Reseau(self.pages)
        self.bibliotheque, self.copie = {}, {}
        for cible, nom, valeur in (
                (B, "_fetch_raw", self.reseau), (B, "_forum_content", self.copie),
                (B, "_forum_content_dirty", False), (B, "_forum_news_check", -1e9),
                (B, "save_forum_content", lambda force=False: None),
                (B, "quota_exhausted", lambda: False)):
            p = mock.patch.object(cible, nom, valeur)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.dict(B.memory(), {"forum_library": self.bibliotheque})
        p.start()
        self.addCleanup(p.stop)
        B.forum_changed()
        self.addCleanup(B.forum_changed)

    def copier(self, url, titre, contenu, chemin="", age_heures=0.0, structure=True):
        """Range une fiche dans la carte et la copie interne, comme l'aurait fait une lecture."""
        maj = (B.now() - B.timedelta(hours=age_heures)).strftime("%Y-%m-%d %H:%M")
        self.bibliotheque[url] = {"titre": titre, "chemin": chemin, "resume": "", "maj": maj}
        self.copie[url] = {"titre": titre, "chemin": chemin, "contenu": contenu, "liens": [], "maj": maj}
        if structure:
            self.copie[url]["messages"] = len(E.split_posts(contenu))
        B.forum_changed()


class _Flux:
    def __init__(self, morceaux):
        self.morceaux = morceaux

    async def iter_chunked(self, taille):
        for m in self.morceaux:
            yield m


class LireLaPageEntiere(unittest.IsolatedAsyncioTestCase):
    async def test_le_corps_est_lu_jusqu_au_bout(self):
        # Le réseau livre la page en plusieurs morceaux : il faut TOUS les recoller. (Avant, seul le
        # premier morceau était gardé — les réponses en bas de page disparaissaient.)
        reponse = mock.Mock(content=_Flux([b"debut ", b"milieu ", b"fin"]))
        self.assertEqual(await B._read_body(reponse), b"debut milieu fin")

    async def test_plafond_de_taille(self):
        reponse = mock.Mock(content=_Flux([b"a" * 600, b"b" * 600, b"c" * 600]))
        self.assertEqual(len(await B._read_body(reponse, maxi=1000)), 1000)


class LireUnSujet(HorsLigne):
    async def test_toutes_les_pages_tous_les_messages(self):
        sujet = await B.read_topic(B._make_grab(None), SUJET)
        self.assertEqual([(p["id"], p["auteur"]) for p in sujet["posts"]],
                         [(29, "Rol-Vunshi"), (30, "Mulos"), (31, "Rol-Vunshi")])      # 30 : pas en double
        self.assertEqual(len(sujet["pages"]), 2)
        self.assertTrue(sujet["complet"] and sujet["structure"])
        self.assertEqual(sujet["dernier_pid"], 31)
        self.assertIn("── Message 3/3 · Rol-Vunshi · Dim 21 Fév 2021 ──\nDernière réponse", sujet["texte"])
        self.assertEqual(sujet["liens"], [(f"{FORUM}/t7-le-col-de-givre", "le Col")])
        self.assertEqual([label for _u, label in sujet["sections"]], ["Le monde d'Orbis", "Créatures"])

    async def test_un_lien_vers_la_page_2_repart_du_debut(self):
        sujet = await B.read_topic(B._make_grab(None), f"{FORUM}/t3p15-les-linnorms#31")
        self.assertEqual([p["id"] for p in sujet["posts"]], [29, 30, 31])

    async def test_borne_de_pages_signalee(self):
        sujet = await B.read_topic(B._make_grab(None), SUJET, max_pages=0)
        self.assertEqual([p["id"] for p in sujet["posts"]], [29, 30])
        self.assertFalse(sujet["complet"])

    async def test_page_sans_structure_texte_brut(self):
        self.reseau.pages["https://autre.example/article"] = "<html><title>Blog</title><p>Un article.</p></html>"
        sujet = await B.read_topic(B._make_grab(None), "https://autre.example/article")
        self.assertFalse(sujet["structure"])
        self.assertIn("Un article.", sujet["texte"])

    async def test_sujet_illisible(self):
        self.assertIsNone(await B.read_topic(B._make_grab(None), f"{FORUM}/t999-inconnu"))

    async def test_la_lecture_range_le_sujet_dans_la_copie(self):
        revision = B._forum_rev
        sujet = await B.copier_sujet(B._make_grab(None), f"{SUJET}#31")
        fiche = self.copie[SUJET]
        self.assertEqual(sujet["cle"], SUJET)
        self.assertEqual((fiche["messages"], fiche["dernier_pid"]), (3, 31))
        self.assertEqual(fiche["chemin"], "Le monde d'Orbis › Créatures")
        self.assertIn("Dernière réponse", fiche["contenu"])
        self.assertEqual(self.bibliotheque[SUJET]["titre"], "Les Linnorms")     # ajouté à la carte
        self.assertGreater(B._forum_rev, revision)                              # le moteur se réindexera

    async def test_outil_fouiller_forum_avec_un_lien_de_sujet(self):
        resultat = await B.fouiller_forum(SUJET, "roi", question="qui est le roi des Linnorms ?")
        self.assertIn(f"=== SOURCE: {SUJET} (Les Linnorms) ===", resultat)
        self.assertIn("SUJET LU EN ENTIER — 3 message(s) sur 2 page(s)", resultat)
        self.assertIn("reproduits mot pour mot", resultat)
        for morceau in ("dragons sans ailes", "Leur roi est Fafnir", "Dernière réponse : Fafnir dort sous le glacier."):
            self.assertIn(morceau, resultat)

    async def test_outil_lire_page_lit_aussi_le_sujet_en_entier(self):
        resultat = await B.tool_lire_page(f"{FORUM}/t3p15-les-linnorms")
        self.assertIn("SUJET LU EN ENTIER — 3 message(s) sur 2 page(s)", resultat)
        self.assertIn("dragons sans ailes", resultat)            # le message d'ouverture, page 1

    async def test_forum_injoignable_on_le_dit(self):
        resultat = await B.fouiller_forum(f"{FORUM}/t999-inconnu", "x")
        self.assertTrue(resultat.startswith("[ÉCHEC]"))

    async def test_forum_injoignable_mais_copie_disponible(self):
        self.copier(f"{FORUM}/t50-vieux-sujet", "Vieux sujet",
                    E.render_posts([{"auteur": "A", "date": "d", "texte": "Contenu gardé en copie."}]), age_heures=500)
        resultat = await B.fouiller_forum(f"{FORUM}/t50-vieux-sujet", "x")
        self.assertIn("Contenu gardé en copie.", resultat)
        self.assertIn("le forum n'a pas répondu : copie interne", resultat)


class SujetTropLong(HorsLigne):
    def setUp(self):
        super().setUp()
        self.vus = []

        async def fausses_notes(messages, max_tokens=400, **kw):
            extrait = messages[1]["content"]
            self.vus.append(extrait)
            return mock.Mock(choices=[mock.Mock(message=mock.Mock(content=f"NOTES[{len(self.vus)}]"))])

        p = mock.patch.object(B, "extract_completion", fausses_notes)
        p.start()
        self.addCleanup(p.stop)
        blabla = "Le vent souffle sur la plaine et la caravane avance lentement. " * 40     # ~2 500 car.
        self.posts = [{"auteur": f"Joueur{i % 3}", "date": f"{i} jan", "texte": f"Tour {i}. " + blabla}
                      for i in range(1, 41)]
        self.posts[24]["texte"] += " Le trésor est caché sous le vieux chêne de Tasglev."
        self.contenu = E.render_posts(self.posts)                                          # ~100 000 car.

    async def test_un_sujet_court_est_rendu_tel_quel(self):
        texte, mode = await B.rendre_sujet("── Message 1/1 · A · d ──\nCourt.", budget=1000)
        self.assertEqual((texte, mode), ("── Message 1/1 · A · d ──\nCourt.", "entier"))

    async def test_tout_est_lu_meme_si_tout_ne_peut_pas_etre_recopie(self):
        texte, mode = await B.rendre_sujet(self.contenu, "où est le trésor ?", budget=30000)
        self.assertEqual(mode, "condense")
        self.assertLessEqual(len(texte), 31000)
        self.assertIn("── Message 1/40 · Joueur1 · 1 jan ──\nTour 1.", texte)         # le début, mot pour mot
        self.assertIn("NOTES[1]", texte)
        # Chaque message au-delà du début a été donné à lire au modèle d'analyse : rien n'est sauté.
        lu = "\n".join(self.vus)
        debut_recopie = texte.split("[SUITE DU SUJET")[0]
        for i in range(1, 41):
            self.assertTrue(f"Tour {i}. " in lu or f"Tour {i}. " in debut_recopie, f"message {i} jamais lu")
        self.assertLessEqual(len(self.vus), B.CONDENSE_MAX_CHUNKS)
        self.assertTrue(all("QUESTION : où est le trésor ?" in v for v in self.vus))
        # …et le passage qui répond à la question est cité mot pour mot.
        self.assertIn("Le trésor est caché sous le vieux chêne de Tasglev.", texte)

    async def test_sans_modele_d_analyse_le_debut_et_les_bons_passages(self):
        with mock.patch.object(B, "quota_exhausted", lambda: True):
            texte, mode = await B.rendre_sujet(self.contenu, "où est le trésor ?", budget=30000)
        self.assertEqual((mode, self.vus), ("extraits", []))
        self.assertIn("Tour 1.", texte)
        self.assertIn("Le trésor est caché sous le vieux chêne de Tasglev.", texte)
        self.assertLessEqual(len(texte), 31000)

    async def test_sujet_secondaire_extraits_sans_appel_au_modele(self):
        texte, mode = await B.rendre_sujet(self.contenu, "trésor chêne", budget=5000, condenser=False)
        self.assertEqual((mode, self.vus), ("extraits", []))
        self.assertIn("vieux chêne de Tasglev", texte)
        self.assertLessEqual(len(texte), 5600)


class RechercheCommeSurLeWeb(HorsLigne):
    def setUp(self):
        super().setUp()
        remplissage = " ".join(["La neige tombe sur les montagnes du nord, comme chaque hiver."] * 10)
        rendu = lambda *textes: E.render_posts([{"auteur": "Mulos", "date": "1 jan", "texte": t} for t in textes])
        self.copier(f"{FORUM}/t3-les-linnorms", "Les Linnorms", rendu(
            "Les Linnorms sont de grands dragons sans ailes. Leur roi, Fafnir, dort sous le glacier.",
            "Réponse : un Linnorm adulte mesure trente mètres. Salina en a vu un."), "Le monde d'Orbis › Créatures")
        self.copier(f"{FORUM}/t8-salina-vaern", "Salina Vaern — prêtresse de Tasglev", rendu(
            "Salina est née à Tasglev. " + remplissage), "Personnages")
        self.copier(f"{FORUM}/t9-borin", "Borin, capuche noire", rendu(
            remplissage + " Borin a juré de tuer Fafnir."), "Personnages")
        self.copier(f"{FORUM}/t10-le-marche", "Le marché aux poissons", rendu(remplissage))

    async def test_resultats_classes_puis_lecture_integrale_des_meilleurs(self):
        resultat = await B.recherche_forum("Fafnir", "qui est Fafnir ?")
        self.assertIn("RÉSULTATS DE LA RECHERCHE SUR LE FORUM pour « Fafnir » (question : qui est Fafnir ?)", resultat)
        # « Fafnir » n'est dans AUCUN titre : les deux sujets sont trouvés par leur TEXTE.
        self.assertIn("1. Les Linnorms — Le monde d'Orbis › Créatures  [LU EN ENTIER CI-DESSOUS]", resultat)
        self.assertIn("Borin, capuche noire", resultat)
        self.assertNotIn("Le marché aux poissons", resultat)
        # Le meilleur sujet est lu EN ENTIER : le message d'ouverture ET la réponse.
        self.assertIn("SUJET LU EN ENTIER — 2 message(s)", resultat)
        self.assertIn("Leur roi, Fafnir, dort sous le glacier.", resultat)
        self.assertIn("Réponse : un Linnorm adulte mesure trente mètres.", resultat)
        self.assertTrue(resultat.startswith(B.WEB_WRITE_DIRECTIVE))

    async def test_les_mots_de_la_question_ne_designent_pas_un_sujet(self):
        # « neige » n'est que dans la question : le marché aux poissons (qui ne parle que de neige)
        # n'est pas un résultat pour « Fafnir ».
        resultat = await B.recherche_forum("Fafnir", "Fafnir a-t-il déjà vu la neige ?")
        self.assertNotIn("Le marché aux poissons", resultat)
        self.assertIn("1. Les Linnorms", resultat)

    async def test_mots_cles_steriles_on_retente_avec_la_question(self):
        resultat = await B.recherche_forum("xqzzyk", "qui a juré de tuer Fafnir ?")
        self.assertIn("Borin, capuche noire", resultat)

    async def test_copie_fraiche_aucune_relecture(self):
        await B.recherche_forum("Fafnir")
        self.assertEqual([u for u in self.reseau.demandes if "/t" in u.replace(FORUM, "")], [])

    async def test_copie_d_avant_la_lecture_par_messages_relue_en_direct(self):
        # Une copie de l'ancien format (texte d'un bloc, souvent tronqué) n'est jamais « fraîche ».
        self.copier(f"{FORUM}/t3-les-linnorms", "Les Linnorms", "Vieux texte sur Fafnir.", structure=False)
        await B.recherche_forum("Fafnir")
        self.assertIn(f"{FORUM}/t3-les-linnorms", self.reseau.demandes)
        self.assertEqual(self.copie[f"{FORUM}/t3-les-linnorms"]["messages"], 3)

    async def test_copie_ancienne_le_sujet_est_relu_en_direct(self):
        self.copier(f"{FORUM}/t3-les-linnorms", "Les Linnorms",
                    E.render_posts([{"auteur": "Mulos", "date": "1 jan", "texte": "Vieux texte sur Fafnir."}]),
                    age_heures=48)
        resultat = await B.recherche_forum("Fafnir")
        self.assertIn(f"{FORUM}/t3-les-linnorms", self.reseau.demandes)
        self.assertIn("lu en direct sur le forum à l'instant", resultat)
        self.assertIn("Dernière réponse : Fafnir dort sous le glacier.", resultat)     # page 2 du sujet
        self.assertEqual(self.copie[f"{FORUM}/t3-les-linnorms"]["messages"], 3)       # copie remise à jour

    async def test_fiches_liees_aux_noms_cites(self):
        resultat = await B.recherche_forum("Linnorms")
        self.assertIn("=== FICHES LIÉES", resultat)
        self.assertIn(f"• Salina Vaern — prêtresse de Tasglev — {FORUM}/t8-salina-vaern", resultat)

    async def test_nouveaute_du_forum_integree_avant_la_recherche(self):
        self.reseau.pages[B.FORUM_URL] = (
            '<html><body><h3><a href="/t77-le-kraken">Le Kraken</a></h3>'
            '<a href="/t77-le-kraken#500">dernier message</a></body></html>')
        self.reseau.pages[f"{FORUM}/t77-le-kraken"] = page(
            [(500, "Mulos", "aujourd'hui", "Le Kraken garde les abysses de Skaldia.")], titre="Le Kraken")
        resultat = await B.recherche_forum("Kraken abysses")
        self.assertIn("1. Le Kraken", resultat)
        self.assertIn("Le Kraken garde les abysses de Skaldia.", resultat)

    async def test_rien_trouve_on_le_dit(self):
        resultat = await B.recherche_forum("zzzzqqqq")
        self.assertIn("AUCUN RÉSULTAT", resultat)
        self.assertNotIn("=== SOURCE:", resultat)

    async def test_recensement_liste_plus_longue(self):
        resultat = await B.recherche_forum("liste tous les personnages qui ont vu la neige")
        self.assertIn("Le marché aux poissons", resultat)

    async def test_sans_copie_interne_on_retombe_sur_l_exploration(self):
        self.bibliotheque.clear()
        self.copie.clear()
        B.forum_changed()
        self.assertIsNone(await B.recherche_forum("Fafnir"))
        with mock.patch.object(B, "_fouiller_forum_crawl", mock.AsyncMock(return_value="exploration")) as crawl:
            self.assertEqual(await B.fouiller_forum(B.FORUM_URL, "Fafnir"), "exploration")
            crawl.assert_awaited_once()

    async def test_une_section_reste_exploree_page_par_page(self):
        with mock.patch.object(B, "_fouiller_forum_crawl", mock.AsyncMock(return_value="section")) as crawl:
            await B.fouiller_forum(f"{FORUM}/f2-les-heros-incarnes", "héros", strict=True)
            crawl.assert_awaited_once_with(f"{FORUM}/f2-les-heros-incarnes", "héros", strict=True)

    async def test_consulter_forum_cite_le_passage_qui_parle_du_sujet(self):
        resultat = await B.consulter_forum("Fafnir")
        self.assertIn("=== Les Linnorms ===", resultat)
        self.assertIn("Borin a juré de tuer Fafnir.", resultat)

    async def test_recherche_du_panneau(self):
        trouves = B.forum_search("fafnir")
        self.assertEqual(trouves[0]["url"], f"{FORUM}/t3-les-linnorms")
        self.assertEqual(set(trouves[0]), {"url", "titre", "chemin", "extrait", "copie"})


class LeModeleRecoitToutLeSujet(unittest.IsolatedAsyncioTestCase):
    """Entre l'outil et le modèle, le résultat d'une lecture de forum ne doit pas être rogné."""

    async def _resultat_transmis(self, outil, arguments, taille=40000):
        recu = []

        async def faux_modele(messages, tools=None, **kw):
            if len(messages) == 2:
                appel = mock.Mock(id="a", function=mock.Mock(arguments=arguments))
                appel.function.name = outil
                return mock.Mock(choices=[mock.Mock(message=mock.Mock(content="", tool_calls=[appel]),
                                                    finish_reason="stop")])
            recu.append(messages[-1]["content"])
            return mock.Mock(choices=[mock.Mock(message=mock.Mock(content="ok", tool_calls=None),
                                                finish_reason="stop")])

        with mock.patch.object(B, "llm_completion", faux_modele), \
                mock.patch.object(B, "execute_tool", mock.AsyncMock(return_value="x" * taille)), \
                mock.patch.object(B, "log_tool_call", lambda *a, **k: None):
            await B.chat_with_tools("sys", [{"role": "user", "content": "q"}], None, tools=B.PUBLIC_TOOLS)
        return len(recu[0])

    async def test_fouille_du_forum(self):
        self.assertEqual(await self._resultat_transmis("fouiller_forum", '{"sujet": "Linnorms"}'), 40000)

    async def test_lire_page_sur_un_sujet_du_forum(self):
        urls = '{"urls": "https://orbis-naturae.forumactif.com/t3-les-linnorms"}'
        self.assertEqual(await self._resultat_transmis("lire_page", urls), 40000)

    async def test_lire_page_ailleurs_reste_borne(self):
        urls = '{"urls": "https://example.org/article"}'
        self.assertEqual(await self._resultat_transmis("lire_page", urls), B.WEB_TOOL_RESULT_MAX)


if __name__ == "__main__":
    unittest.main()
