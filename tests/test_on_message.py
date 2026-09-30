"""on_message de bout en bout, hors ligne : on capture ce qui PARTIRAIT au modèle (prompt,
outils, chaleur, hôtes lisibles) sans appeler ni Discord ni Mistral."""
import unittest
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

from support import Typing, load_bot

B = load_bot()

FORUM = "orbis-naturae.forumactif.com"
SERVEUR_ORBIS, SERVEUR_AUTRE, SALON, JOUEUR = 111, 112, 222, 333


class OnMessage(unittest.IsolatedAsyncioTestCase):
    route = "chat"

    def setUp(self):
        self.captures = []
        self.outils_utilises = set()

        async def faux_chat(system_prompt, thread, guild, tools=None, **kw):
            self.captures.append({
                "prompt": system_prompt,
                "outils": {t["function"]["name"] for t in (tools or [])},
                "hotes": kw.get("allowed_hosts"),
                "chaleur": kw.get("temperature"),
            })
            return "réponse", set(self.outils_utilises)

        async def fausse_route(*a, **k):
            return self.route

        moi = MagicMock(id=999)
        moi.mentioned_in = lambda m: True
        self.conseil = AsyncMock(return_value="")
        self.humeur = AsyncMock()
        remplacements = [
            (B, "chat_with_tools", faux_chat), (B, "resolve_route", fausse_route),
            (B, "deliberate", self.conseil), (B, "update_self_state", self.humeur),
            (B, "send_reply", AsyncMock()), (B, "auto_extract_memories", AsyncMock()),
            (B, "get_guild_context", lambda message: "Serveur de test."),
            (B, "get_user_context", lambda *a, **k: ""),
            (B, "member_notes_block", lambda *a, **k: ""),
            (B, "get_cross_user_context", lambda *a, **k: ""),
            (B, "conversations", {}), (B, "summaries", {}),
            (B.bot, "process_commands", AsyncMock()), (B.bot._connection, "user", moi),
        ]
        for cible, nom, faux in remplacements:
            p = mock.patch.object(cible, nom, faux)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.dict(B.memory(), {"forum_library": {
            f"https://{FORUM}/t2-lorenzo": {"titre": "Lorenzo Stenode — Maître canonnier",
                                            "chemin": "Personnages › Les héros incarnés"},
            f"https://{FORUM}/t3-linnorms": {"titre": "Les Linnorms",
                                             "chemin": "Le monde d'Orbis › Continent de Skaldia"},
        }})
        p.start()
        self.addCleanup(p.stop)
        B._title_names_cache["cle"] = None
        B.forum_changed()                       # la carte a changé : le moteur se réindexe
        B._forum_grace.clear()
        B._tool_grace.clear()
        B._channel_threads.pop(SALON, None)
        B.set_guild_setting(SERVEUR_ORBIS, "forum_orbis", True)

    async def envoyer(self, texte, serveur=SERVEUR_ORBIS, outils_utilises=()):
        self.outils_utilises = set(outils_utilises)
        m = MagicMock()
        m.author.id, m.author.name, m.author.display_name, m.author.bot = JOUEUR, "joueur", "Joueur", False
        m.channel.id, m.channel.name, m.channel.nsfw = SALON, "general", False
        m.channel.typing = lambda: Typing()
        m.guild.id, m.guild.name, m.guild.members = serveur, "Serveur", []
        m.content, m.mentions, m.reference = texte, [], None
        m.reply, m.add_reaction = AsyncMock(), AsyncMock()
        await B.on_message(m)
        self.assertFalse(m.reply.called, "on_message a levé une exception (voir la trace)")
        return self.captures[-1]


class SourceUnique(OnMessage):
    async def test_question_sans_signal_ni_web_ni_forum(self):
        c = await self.envoyer("c'est quoi les Skavens ?")
        self.assertFalse({"recherche_web", "fouiller_forum", "consulter_forum"} & c["outils"])
        self.assertIn(B.ORBIS_ONLY_DIRECTIVE, c["prompt"])
        self.assertIn(B.FORUM_INTERNAL_DIRECTIVE, c["prompt"])
        self.assertEqual(c["hotes"], {FORUM})

    async def test_nom_d_une_fiche_connue_garde_les_outils_du_forum(self):
        c = await self.envoyer("c'est qui lorenzo ?")
        self.assertIn("fouiller_forum", c["outils"])
        self.assertNotIn("recherche_web", c["outils"])
        self.assertIn("« Lorenzo Stenode — Maître canonnier »", c["prompt"])
        self.assertNotIn(B.FORUM_INTERNAL_DIRECTIVE, c["prompt"])

    async def test_relance_apres_une_fouille(self):
        await self.envoyer("parle-moi du lore des Linnorms sur le forum", outils_utilises={"fouiller_forum"})
        c = await self.envoyer("et leur roi, il s'appelle comment ?")
        self.assertIn("fouiller_forum", c["outils"])
        self.assertIn("tu viens de fouiller le forum", c["prompt"])

    async def test_internet_sur_demande_explicite_seulement(self):
        c = await self.envoyer("cherche sur internet la météo à Paris demain")
        self.assertIn("recherche_web", c["outils"])

    async def test_lien_donne_par_la_personne(self):
        c = await self.envoyer("lis https://example.org/article et dis-moi ce que ça raconte")
        self.assertEqual(c["hotes"], {FORUM, "example.org"})

    async def test_serveur_sans_forum_orbis_inchange(self):
        c = await self.envoyer("c'est quoi les Skavens ?", serveur=SERVEUR_AUTRE)
        self.assertIn("recherche_web", c["outils"])
        self.assertNotIn("fouiller_forum", c["outils"])
        self.assertIsNone(c["hotes"])
        self.assertIn(B.ORBIS_OFF_DIRECTIVE, c["prompt"])


class VoixEtConversation(OnMessage):
    """Ses outils lui sont tendus presque toujours : ça ne doit pas lui couper la voix."""

    async def test_message_ordinaire_outils_ET_voix(self):
        for serveur in (SERVEUR_ORBIS, SERVEUR_AUTRE):
            with self.subTest(serveur=serveur):
                c = await self.envoyer("t'as passé une bonne journée ou pas trop ?", serveur=serveur)
                self.assertTrue(c["outils"], "les outils restent proposés")
                self.assertIn(B.VOIX, c["prompt"])
                self.assertIn(B.NATUREL_DISCORD, c["prompt"])
                self.assertIn("TON ÉTAT INTÉRIEUR", c["prompt"])
                self.assertEqual(c["chaleur"], 0.95)

    async def test_fouille_demandee_restitution_carree(self):
        c = await self.envoyer("dis-moi tout sur les Linnorms d'après le forum")
        self.assertIn(B.FORUM_FIRST_DIRECTIVE, c["prompt"])
        self.assertNotIn(B.VOIX, c["prompt"])
        self.assertNotIn(B.NATUREL_DISCORD, c["prompt"])
        self.assertEqual(c["chaleur"], 0.85)

    async def test_l_humeur_evolue_apres_une_conversation_pas_apres_un_outil(self):
        await self.envoyer("t'as passé une bonne journée ou pas trop ?")
        self.assertEqual(self.humeur.call_count, 1)
        await self.envoyer("lance-moi un d20 pour voir", outils_utilises={"lancer_des"})
        self.assertEqual(self.humeur.call_count, 1)


class SceneDeJeuDeRole(OnMessage):
    route = "roleplay"

    async def test_pas_de_voix_de_conversation_en_pleine_scene(self):
        c = await self.envoyer("*pousse la porte de la crypte, la torche à la main*")
        self.assertIn(B.RP_PROMPT_SUFFIX, c["prompt"])
        self.assertNotIn(B.VOIX, c["prompt"])
        self.assertNotIn(B.NATUREL_DISCORD, c["prompt"])
        self.assertEqual(c["chaleur"], 0.85)
        self.conseil.assert_not_called()


class ConseilInterieur(OnMessage):
    QUESTION = ("Je n'arrive pas à choisir entre Rust et Go pour mon prochain simulateur, "
                "pourquoi tu prendrais l'un plutôt que l'autre ?")

    async def test_reuni_sur_une_vraie_question(self):
        await self.envoyer(self.QUESTION, serveur=SERVEUR_AUTRE)
        self.conseil.assert_awaited_once()
        self.assertEqual(self.conseil.await_args.kwargs["cloison"], "")

    async def test_tenu_a_la_meme_cloison_sur_un_serveur_orbis(self):
        await self.envoyer(self.QUESTION)
        self.assertEqual(self.conseil.await_args.kwargs["cloison"], B.ORBIS_ONLY_DIRECTIVE)

    async def test_pas_reuni_quand_un_outil_doit_d_abord_chercher(self):
        for texte in (
            "résume ce qui s'est dit dans le salon général hier soir et explique pourquoi ça s'est énervé",
            "cherche sur internet pourquoi le ciel est bleu et explique-moi ça en détail s'il te plaît",
            "lance 14 attaques à 1d100, objectif 70, et explique-moi comment tu comptes les dégâts",
            "explique-moi en détail qui sont les Linnorms d'après le forum, et pourquoi on les craint",
            "c'est qui lorenzo au juste, et pourquoi tout le monde a l'air de le détester autant ?",
        ):
            with self.subTest(texte=texte):
                self.conseil.reset_mock()
                await self.envoyer(texte)
                self.conseil.assert_not_called()

    async def test_pas_reuni_pour_du_bavardage(self):
        await self.envoyer("salut !")
        self.conseil.assert_not_called()


if __name__ == "__main__":
    unittest.main()
