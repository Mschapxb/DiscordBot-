"""Source unique : sur un serveur Orbis, elle ne cherche que sur le forum officiel."""
import unittest
from unittest import mock

from support import load_bot

B = load_bot()

FORUM = "orbis-naturae.forumactif.com"
BIBLIOTHEQUE = {
    f"https://{FORUM}/t1-teowyne": {"titre": "Téowyne Hilate — moniale d'Aémée",
                                    "chemin": "Personnages › Les héros incarnés"},
    f"https://{FORUM}/t2-lorenzo": {"titre": "Lorenzo Stenode — Maître canonnier",
                                    "chemin": "Personnages › Les héros incarnés"},
    f"https://{FORUM}/t3-linnorms": {"titre": "Les Linnorms",
                                     "chemin": "Le monde d'Orbis › Continent de Skaldia"},
    f"https://{FORUM}/t4-orga": {"titre": "Organisation théologique",
                                 "chemin": "Le monde d'Orbis › Continent d'Aedmosie"},
}


def noms(outils):
    return {t["function"]["name"] for t in (outils or [])}


class AvecBibliotheque:
    """Mixin : installe une fausse carte du forum le temps du test."""

    def setUp(self):
        super().setUp()
        p = mock.patch.dict(B.memory(), {"forum_library": dict(BIBLIOTHEQUE)})
        p.start()
        self.addCleanup(p.stop)
        B._title_names_cache["cle"] = None          # la carte a changé : on oublie le cache


class SignalWeb(unittest.TestCase):
    def test_une_question_n_est_pas_une_demande_d_internet(self):
        for texte in ("c'est quoi un Linnorm ?", "le webhook marche ?", "regarde le wiki", ""):
            with self.subTest(texte=texte):
                self.assertFalse(B.web_signal(texte))

    def test_demande_explicite(self):
        for texte in ("cherche sur internet la sortie du jeu", "tu peux googler ça ?",
                      "regarde sur le web", "vérifie sur Wikipédia", "trouve ça sur le net"):
            with self.subTest(texte=texte):
                self.assertTrue(B.web_signal(texte))


class Perimetre(unittest.TestCase):
    def test_recherche_web_retiree_sans_demande_explicite(self):
        outils, hotes = B.orbis_source_scope(B.PUBLIC_TOOLS, "c'est quoi les Skavens ?")
        self.assertNotIn("recherche_web", noms(outils))
        self.assertIn("fouiller_forum", noms(outils))
        self.assertEqual(hotes, {FORUM})

    def test_recherche_web_gardee_sur_demande_explicite(self):
        outils, _ = B.orbis_source_scope(B.PUBLIC_TOOLS, "cherche sur le web la météo")
        self.assertIn("recherche_web", noms(outils))

    def test_un_lien_donne_par_quelqu_un_devient_lisible(self):
        _, hotes = B.orbis_source_scope(None, "lis https://www.example.org/page stp",
                                        ["avant : https://autre.example/x"])
        self.assertEqual(hotes, {FORUM, "example.org", "autre.example"})


class NomsPropresDesTitres(unittest.TestCase):
    def test_titres_du_forum(self):
        cas = {
            "Téowyne Hilate — moniale d'Aémée": {"teowyne", "hilate", "aemee"},
            "Lorenzo Stenode — Maître canonnier": {"lorenzo", "stenode"},
            "Les Linnorms": {"linnorms"},
            "Linnorms": {"linnorms"},
            "Le monde d'Orbis › Continent de Skaldia": {"skaldia"},
            # Des mots courants ne doivent pas envoyer la conversation sur le forum :
            "Les champs hérissés - cimetière d'autrefois": set(),
            "Organisation théologique": set(),
            "Expédition punitive - il fait froid dans le dos de l'Empire": set(),
            "L'Illumination par la sagesse des saints érudits omnipotents": set(),
        }
        for titre, attendu in cas.items():
            with self.subTest(titre=titre):
                self.assertEqual(B._proper_nouns_of_title(titre), attendu)


class FichesNommees(AvecBibliotheque, unittest.TestCase):
    def test_message_qui_nomme_une_fiche(self):
        self.assertEqual(B.forum_titles_in_text("c'est qui lorenzo ?"),
                         ["Lorenzo Stenode — Maître canonnier"])
        self.assertEqual(B.forum_titles_in_text("c'est quoi un linnorm ?"), ["Les Linnorms"])
        self.assertEqual(len(B.forum_titles_in_text("parle-moi de Skaldia")), 1)

    def test_conversation_ordinaire(self):
        for texte in ("oui maître, tout de suite", "c'est quoi l'organisation du serveur ?",
                      "tu fais quoi ce soir ?"):
            with self.subTest(texte=texte):
                self.assertEqual(B.forum_titles_in_text(texte), [])

    def test_bibliotheque_vide(self):
        with mock.patch.dict(B.memory(), {"forum_library": {}}):
            B._title_names_cache["cle"] = None
            self.assertEqual(B.forum_titles_in_text("c'est qui lorenzo ?"), [])


class RelanceApresFouille(unittest.TestCase):
    def setUp(self):
        B._forum_grace.clear()

    def test_armee_par_une_fouille_puis_s_eteint(self):
        B.update_forum_grace(42, {"fouiller_forum"})
        self.assertEqual(B._forum_grace[42], B.FORUM_GRACE_TURNS)
        for _ in range(B.FORUM_GRACE_TURNS + 1):
            B.update_forum_grace(42, set())
        self.assertEqual(B._forum_grace[42], 0)

    def test_un_autre_outil_ne_l_arme_pas(self):
        B.update_forum_grace(7, {"lancer_des"})
        self.assertEqual(B._forum_grace.get(7, 0), 0)


class OutilsDeLecture(AvecBibliotheque, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.lus, self.fouilles = [], []

        async def faux_fetch(url, session=None):
            self.lus.append(url)
            return {"url": url, "title": "T", "text": "contenu"}

        async def fausse_fouille(url, sujet="", strict=False):
            self.fouilles.append((url, sujet, strict))
            return "ok"

        for nom, faux in (("fetch_url_text", faux_fetch), ("fouiller_forum", fausse_fouille)):
            p = mock.patch.object(B, nom, faux)
            p.start()
            self.addCleanup(p.stop)
        self.hotes = B.orbis_allowed_hosts("regarde https://example.org/a")

    async def test_lire_page_refuse_une_url_que_personne_n_a_donnee(self):
        resultat = await B.execute_tool("lire_page", {"urls": (
            "https://warhammer.fandom.com/wiki/Skaven "
            f"https://{FORUM}/t3-linnorms https://example.org/a")}, None, allowed_hosts=self.hotes)
        self.assertIn("[REFUSÉ] https://warhammer.fandom.com/wiki/Skaven", resultat)
        self.assertEqual(self.lus, [f"https://{FORUM}/t3-linnorms", "https://example.org/a"])

    async def test_lire_page_libre_hors_serveur_orbis(self):
        await B.execute_tool("lire_page", {"urls": "https://warhammer.fandom.com/wiki/Skaven"}, None)
        self.assertEqual(self.lus, ["https://warhammer.fandom.com/wiki/Skaven"])

    async def test_fouiller_forum_ramene_une_url_exterieure_sur_le_forum(self):
        await B.execute_tool("fouiller_forum",
                             {"sujet": "zzz", "url": "https://warhammer.fandom.com/wiki/Skaven"},
                             None, allowed_hosts=self.hotes)
        self.assertEqual(self.fouilles[-1][0], B.FORUM_URL)

    async def test_fouiller_forum_resout_un_lien_relatif_de_section(self):
        await B.execute_tool("fouiller_forum", {"sujet": "héros", "url": "/f2-les-heros-incarnes"},
                             None, allowed_hosts=self.hotes)
        self.assertEqual(self.fouilles[-1], (f"https://{FORUM}/f2-les-heros-incarnes", "héros", True))

    async def test_fouiller_forum_part_de_la_fiche_connue(self):
        await B.execute_tool("fouiller_forum", {"sujet": "linnorm"}, None, allowed_hosts=self.hotes)
        self.assertTrue(self.fouilles[-1][0].endswith("/t3-linnorms"))


# --- Faux modèle : mêmes attributs que ceux lus par chat_with_tools ---
class _Fn:
    def __init__(self, nom, arguments):
        self.name, self.arguments = nom, arguments


class _Appel:
    def __init__(self, ident, nom, arguments="{}"):
        self.id, self.function = ident, _Fn(nom, arguments)


class _Reponse:
    def __init__(self, texte="", appels=None):
        message = mock.Mock(content=texte, tool_calls=appels)
        self.choices = [mock.Mock(message=message, finish_reason="stop")]


class BoucleOutils(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.executes, self.tours = [], []

        async def espion(nom, args, *a, **k):
            self.executes.append((nom, k.get("allowed_hosts")))
            return "résultat"

        async def faux_modele(messages, route="chat", tools=None, temperature=None, **kw):
            self.tours.append({"outils": noms(tools), "temperature": temperature})
            if len(self.tours) == 1:     # elle réclame un outil NON proposé et un outil proposé
                return _Reponse(appels=[_Appel("a", "recherche_web", '{"requete": "skaven"}'),
                                        _Appel("b", "lancer_des", '{"expression": "1d6"}')])
            return _Reponse("Rien trouvé sur le forum.")

        for nom, faux in (("execute_tool", espion), ("llm_completion", faux_modele),
                          ("log_tool_call", lambda *a, **k: None)):
            p = mock.patch.object(B, nom, faux)
            p.start()
            self.addCleanup(p.stop)

    async def test_un_outil_non_propose_n_est_jamais_execute(self):
        outils, hotes = B.orbis_source_scope(B.PUBLIC_TOOLS, "c'est quoi les Skavens ?")
        texte, utilises = await B.chat_with_tools(
            "sys", [{"role": "user", "content": "c'est quoi les Skavens ?"}], None,
            tools=outils, allowed_hosts=hotes, temperature=0.95)
        self.assertNotIn("recherche_web", self.tours[0]["outils"])
        self.assertEqual(self.executes, [("lancer_des", hotes)])
        self.assertEqual(utilises, {"lancer_des"})
        self.assertEqual(texte, "Rien trouvé sur le forum.")

    async def test_la_chaleur_retombe_des_qu_un_outil_a_servi(self):
        await B.chat_with_tools("sys", [{"role": "user", "content": "lance un dé"}], None,
                                tools=B.PUBLIC_TOOLS, temperature=0.95)
        self.assertEqual([t["temperature"] for t in self.tours], [0.95, 0.85])


class Directives(unittest.TestCase):
    def test_cloison(self):
        self.assertIn("Warhammer", B.ORBIS_ONLY_DIRECTIVE)
        self.assertIn(B.FORUM_URL, B.ORBIS_ONLY_DIRECTIVE)

    def test_cas_intermediaire(self):
        d = B.forum_maybe_directive(["Les Linnorms"], suite=True)
        self.assertIn("« Les Linnorms »", d)
        self.assertIn("tu viens de fouiller le forum", d)


if __name__ == "__main__":
    unittest.main()
