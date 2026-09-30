"""forum_engine : lecture d'un sujet message par message, et moteur de recherche du forum."""
import unittest

import support  # noqa: F401  (ajoute la racine du dépôt au chemin d'import)
import forum_engine as E

# Une page de sujet au format du thème du forum (AwesomeBB) : deux messages, et entre eux le
# bloc publicitaire que Forumactif glisse sous l'identifiant « post-0 ».
PAGE_AWESOMEBB = """
<html><head><title>Les Linnorms</title><script>var x = "<div id='post-99' class='post'>piège</div>";</script></head>
<body><main id="topic"><div class="topic-header"><h1><a href="/t3-les-linnorms">Les Linnorms</a></h1></div>
<div id="post-29" class="post-wrap row2 post--29 ">
  <div id="29" class="post-header"><h2><span class="post-heading-wrap"><a href="/t3-les-linnorms#29">Les Linnorms</a>
    <span class="post-date">Ven 19 Fév 2021 - 19:36</span></span></h2>
    <div class="mobile-hide post-buttons"><ul><li class="btn-quote">Citer</li></ul></div></div>
  <div class="post-body"><div class="post"><div class="post-content">
    Les Linnorms sont des dragons sans ailes.<br /><br />Leur roi se nomme <strong>Fafnir l&#8217;Ancien</strong>,
    voir <a href="/t7-le-col-de-givre">le Col de Givre</a>.
    <div class="signature_div">Ma signature inutile</div>
  </div><div class="post-footer">pied</div></div>
  <aside class="post-aside"><div class="post-author"><span class="post-author-name">Rol-Vunshi</span>
    <span class="post-author-title">Tribun</span></div><dl class="post-author-details"><dd>275</dd></dl></aside></div>
</div>
<div id="post-0" class="post-wrap row2 post--0 "><div class="post-body"><div class="post"><div class="post-content">
  </div></div><aside class="post-aside"><span class="post-author-name">Contenu sponsorisé</span></aside></div></div>
<div id="post-30" class="post-wrap row1 post--30 ">
  <div id="30" class="post-header"><h2><span class="post-heading-wrap"><a href="#30">Re: Les Linnorms</a>
    <span class="post-date">Sam 20 Fév 2021 - 8:02</span></span></h2></div>
  <div class="post-body"><div class="post"><div class="post-content">
    <blockquote><cite>Rol-Vunshi a écrit:</cite><div>Leur roi se nomme Fafnir</div></blockquote>
    Je confirme : Fafnir dort sous le <a href="https://ailleurs.example/x">glacier</a>.<p>par Mulos</a></p>
  </div></div><aside class="post-aside"><span class="post-author-name">Mulos</span></aside></div>
</div></main></body></html>
"""

# Le même sujet dans un thème phpBB3 (prosilver) : id="p29", auteur et date dans <p class="author">.
PAGE_PROSILVER = """
<div id="p29" class="post row1"><div class="postbody">
  <h2 class="topic-title">Les Linnorms</h2>
  <p class="author">par <strong><a href="/u1">Rol-Vunshi</a></strong> le Ven 19 Fév 2021 - 19:36</p>
  <div class="content clearfix"><div>Des dragons sans ailes.</div></div></div>
  <div class="postprofile"><dl><dd>Messages : 275</dd></dl></div></div>
<div id="p30" class="post row2"><div class="postbody">
  <p class="author">par <strong>Jean Marc</strong> le Sam 20 Fév 2021 - 8:02</p>
  <div class="content clearfix"><div>Je confirme.</div></div></div></div>
"""


class LectureDUnSujet(unittest.TestCase):
    def test_messages_auteurs_et_dates(self):
        page = E.parse_topic_page(PAGE_AWESOMEBB)
        self.assertEqual(page["titre"], "Les Linnorms")
        self.assertEqual([(p["id"], p["auteur"], p["date"]) for p in page["posts"]],
                         [(29, "Rol-Vunshi", "Ven 19 Fév 2021 - 19:36"),
                          (30, "Mulos", "Sam 20 Fév 2021 - 8:02")])

    def test_le_corps_du_message_et_rien_d_autre(self):
        premier, reponse = E.parse_topic_page(PAGE_AWESOMEBB)["posts"]
        self.assertIn("Les Linnorms sont des dragons sans ailes.", premier["texte"])
        self.assertIn("Fafnir l’Ancien", premier["texte"])            # entités HTML décodées
        for parasite in ("signature", "Citer", "Tribun", "275", "pied", "piège"):
            self.assertNotIn(parasite, premier["texte"])
        self.assertIn("[citation]", reponse["texte"])                  # la citation est balisée…
        self.assertIn("Je confirme : Fafnir dort sous le glacier.", reponse["texte"])

    def test_le_bloc_publicitaire_n_est_pas_un_message(self):
        self.assertNotIn(0, [p["id"] for p in E.parse_topic_page(PAGE_AWESOMEBB)["posts"]])

    def test_liens_cites_dans_les_messages(self):
        premier, reponse = E.parse_topic_page(PAGE_AWESOMEBB)["posts"]
        self.assertEqual(premier["liens"], [("/t7-le-col-de-givre", "le Col de Givre")])
        self.assertEqual(reponse["liens"], [("https://ailleurs.example/x", "glacier")])

    def test_theme_phpbb3(self):
        posts = E.parse_topic_page(PAGE_PROSILVER)["posts"]
        self.assertEqual([(p["id"], p["auteur"], p["date"], p["texte"]) for p in posts],
                         [(29, "Rol-Vunshi", "Ven 19 Fév 2021 - 19:36", "Des dragons sans ailes."),
                          (30, "Jean Marc", "Sam 20 Fév 2021 - 8:02", "Je confirme.")])

    def test_message_qui_ne_contient_qu_une_image(self):
        html = ('<div id="post-5" class="post-wrap post--5"><div class="post-content"><a href="x.jpg">'
                '<img src="x.jpg" alt="Tsita"/></a></div><aside><span class="post-author-name">mschap</span>'
                '<dl><dt>Messages :</dt><dd>78</dd></dl></aside></div>')
        (msg,) = E.parse_topic_page(html)["posts"]
        self.assertEqual((msg["auteur"], msg["texte"]), ("mschap", "(message sans texte — 1 image(s) seulement)"))
        # …et ce texte de remplacement n'est pas indexé par le moteur.
        idx = E.ForumIndex.build([{"url": "u", "titre": "Tsita", "contenu": E.render_posts([msg])}])
        self.assertEqual(idx.search("image"), [])
        self.assertEqual(idx.search("Tsita")[0]["url"], "u")

    def test_page_sans_structure_de_forum(self):
        self.assertEqual(E.parse_topic_page("<html><body><p>Une page web ordinaire.</p></body></html>")["posts"], [])
        self.assertEqual(E.parse_topic_page("")["posts"], [])

    def test_aller_retour_avec_la_copie_interne(self):
        posts = E.parse_topic_page(PAGE_AWESOMEBB)["posts"]
        texte = E.render_posts(posts)
        self.assertIn("── Message 2/2 · Mulos · Sam 20 Fév 2021 - 8:02 ──", texte)
        relus = E.split_posts(texte)
        self.assertEqual([(p["n"], p["auteur"], p["date"], p["texte"]) for p in relus],
                         [(i, p["auteur"], p["date"], p["texte"]) for i, p in enumerate(posts, 1)])

    def test_ancienne_copie_sans_en_tete(self):
        self.assertEqual(E.split_posts("Un vieux texte d'un seul bloc."),
                         [{"n": 1, "auteur": "", "date": "", "texte": "Un vieux texte d'un seul bloc."}])
        self.assertEqual(E.split_posts("   "), [])


class Racines(unittest.TestCase):
    def test_pluriels_et_feminins_se_rejoignent(self):
        for formes in (("Linnorm", "Linnorms"), ("roi", "rois"), ("dieu", "dieux"),
                       ("cheval", "chevaux"), ("château", "châteaux"),
                       ("Skaldien", "Skaldiens", "Skaldienne", "Skaldiennes"),
                       ("empire", "empires"), ("prêtresse", "prêtresses")):
            with self.subTest(formes=formes):
                self.assertEqual(len({tuple(E.termes(f)) for f in formes}), 1)

    def test_les_mots_de_la_question_sont_ecartes(self):
        self.assertEqual(E.termes("Dis-moi tout ce que tu sais sur le roi des Linnorms ?"), ["roi", "linnorm"])


def fiche(url, titre, contenu, chemin="", mots=""):
    return {"url": url, "titre": titre, "chemin": chemin, "mots": mots, "contenu": contenu, "maj": "2026-09-30 10:00"}


def messages(*textes):
    return E.render_posts([{"auteur": f"Auteur{i}", "date": "1 jan", "texte": t} for i, t in enumerate(textes, 1)])


class Recherche(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        remplissage = " ".join(["La neige tombe sur les montagnes du nord, comme chaque hiver."] * 12)
        cls.idx = E.ForumIndex.build([
            fiche("u/linnorms", "Les Linnorms", messages(
                "Les Linnorms sont de grands dragons sans ailes qui hantent les fjords.\n\n"
                "Leur roi, Fafnir l'Ancien, dort sous le glacier de Skaldia.",
                "Un Linnorm adulte mesure trente mètres."), chemin="Le monde d'Orbis › Créatures"),
            fiche("u/salina", "Salina Vaern — prêtresse de Tasglev", messages(
                "Salina est née à Tasglev, capitale de l'Empire Skaldien. Elle sert au Collège des Brumes.",
                remplissage + " Elle a affronté un Linnorm dans sa jeunesse."), chemin="Personnages › Les héros incarnés"),
            fiche("u/tasglev", "Tasglev", messages(
                "Tasglev est la capitale de l'Empire Skaldien, bâtie sur sept collines de basalte."),
                chemin="Le monde d'Orbis › Continent de Skaldia"),
            fiche("u/culte", "Le culte d'Yshma", messages(
                "Les adeptes d'Yshma portent un bandeau noir et vénèrent l'œil.")),
            fiche("u/garde", "Borin, capuche noire", messages(
                remplissage + "\n\nBorin a rejoint le culte d'Yshma après la chute de Tasglev.")),
            fiche("u/carte", "Expédition punitive", ""),          # cartographié, pas encore copié
            fiche("u/bruit", "Le marché aux poissons", messages(remplissage)),
        ])

    def urls(self, requete, **kw):
        return [r["url"] for r in self.idx.search(requete, **kw)]

    def test_le_titre_prime(self):
        self.assertEqual(self.urls("Linnorms")[0], "u/linnorms")
        self.assertEqual(self.urls("Tasglev")[0], "u/tasglev")

    def test_trouve_dans_le_texte_et_pas_seulement_dans_les_titres(self):
        # « Fafnir » et « basalte » n'apparaissent dans AUCUN titre.
        self.assertEqual(self.urls("Fafnir"), ["u/linnorms"])
        self.assertEqual(self.urls("collines de basalte"), ["u/tasglev"])
        # Borin ne porte pas « Yshma » dans son titre, mais sa fiche le dit : il est trouvé.
        self.assertEqual(set(self.urls("Yshma")), {"u/culte", "u/garde"})

    def test_question_en_langage_naturel(self):
        r = self.idx.search("qui est le roi des Linnorms ?")[0]
        self.assertEqual(r["url"], "u/linnorms")
        self.assertIn("Fafnir", r["extrait"])

    def test_un_sujet_qui_a_tous_les_mots_passe_devant(self):
        self.assertEqual(self.urls("capitale Empire Skaldien")[:2], ["u/tasglev", "u/salina"])

    def test_singulier_pluriel_et_variantes_d_un_nom(self):
        self.assertIn("u/linnorms", self.urls("linnorm"))
        self.assertIn("u/tasglev", self.urls("Skaldiens"))            # « Skaldien », « Skaldia »

    def test_faute_de_frappe(self):
        self.assertEqual(self.urls("Tasglef")[0], "u/tasglev")
        self.assertEqual(self.urls("Linorms")[0], "u/linnorms")

    def test_accents_indifferents(self):
        self.assertEqual(self.urls("pretresse")[0], "u/salina")

    def test_expression_exacte_entre_guillemets(self):
        self.assertEqual(self.urls('"bandeau noir"'), ["u/culte"])
        self.assertEqual(self.urls('"bandeau rouge"'), [])

    def test_mots_de_la_meme_famille(self):
        # La fiche dit « capitale » et « bâtie » ; la question dit « bâtir ».
        self.assertEqual(self.urls("bâtir sur des collines")[0], "u/tasglev")

    def test_mots_d_appoint(self):
        # Les mots d'appoint (la question en clair) départagent, mais ne retiennent pas un sujet.
        sans = {r["url"]: r["score"] for r in self.idx.search("Tasglev")}
        avec = {r["url"]: r["score"] for r in self.idx.search("Tasglev", appoint="qui a rejoint le culte ?")}
        self.assertEqual(set(avec), set(sans))                           # « culte » seul ne retient rien
        self.assertNotIn("u/culte", avec)
        self.assertGreater(avec["u/garde"], sans["u/garde"])             # …mais il fait monter Borin
        self.assertEqual(avec["u/tasglev"], sans["u/tasglev"])

    def test_nom_propre_ou_mot_courant(self):
        self.assertTrue(self.idx.mot_courant("neige"))                   # toujours en minuscules
        self.assertFalse(self.idx.mot_courant("tasglev"))                # toujours avec majuscule
        self.assertFalse(self.idx.mot_courant("inconnu"))

    def test_sujet_cartographie_mais_pas_encore_copie(self):
        r = self.idx.search("expédition punitive")[0]
        self.assertEqual((r["url"], r["copie"], r["passages"]), ("u/carte", False, []))

    def test_rien_a_trouver(self):
        self.assertEqual(self.urls("zzzzzz qqqqqq"), [])
        self.assertEqual(self.urls(""), [])

    def test_restreindre_a_certains_sujets(self):
        self.assertEqual(self.urls("Tasglev", urls={"u/salina", "u/garde"})[0], "u/salina")
        self.assertNotIn("u/tasglev", self.urls("Tasglev", urls={"u/salina", "u/garde"}))

    def test_l_extrait_montre_l_endroit_ou_ca_parle_du_sujet(self):
        r = next(r for r in self.idx.search("Borin Yshma") if r["url"] == "u/garde")
        self.assertIn("Yshma", r["extrait"])
        self.assertLess(len(r["extrait"]), 330)

    def test_couverture_de_l_index(self):
        self.assertAlmostEqual(self.idx.couverture, 6 / 7)


class PassagesDUnLongSujet(unittest.TestCase):
    def test_retient_ce_qui_repond_a_la_question_dans_l_ordre_du_sujet(self):
        bla = "Le vent souffle sur la plaine et rien ne se passe ici. " * 30
        contenu = messages(bla, bla + "\n\nLe trésor est caché sous le vieux chêne.", bla,
                           "Plus tard, on apprit que le chêne avait brûlé avec le trésor.")
        texte, retenus, total = E.meilleurs_passages(contenu, "où est le trésor ?", budget=1200)
        self.assertGreater(total, retenus)
        self.assertIn("caché sous le vieux chêne", texte)
        self.assertIn("avait brûlé", texte)
        self.assertLess(texte.index("[message 2"), texte.index("[message 4"))
        self.assertLessEqual(len(texte), 1500)

    def test_decoupage_en_passages(self):
        passages = E._decouper("Phrase courte. " * 200, maxi=300)
        self.assertTrue(all(len(p) <= 300 for p in passages))
        self.assertEqual(" ".join(passages).split(), ("Phrase courte. " * 200).split())


if __name__ == "__main__":
    unittest.main()
