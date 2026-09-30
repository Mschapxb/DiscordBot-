"""Persistance : on ne perd pas la mémoire sur un crash, un fichier abîmé ou un démarrage raté."""
import json
import os
import tempfile
import unittest
from unittest import mock

from support import WORK, load_bot

B = load_bot()


class EcritureAtomique(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(dir=WORK)
        self.path = os.path.join(self.dossier, "memory.json")

    def test_ecrit_le_fichier_sans_laisser_de_temporaire(self):
        B.save_json(self.path, {"souvenirs": ["é", "ü"]})
        self.assertEqual(os.listdir(self.dossier), ["memory.json"])
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"souvenirs": ["é", "ü"]})

    def test_coupure_pendant_l_ecriture_garde_l_ancien_fichier(self):
        B.save_json(self.path, {"version": 1})
        with mock.patch.object(B.os, "fsync", side_effect=OSError("disque plein")):
            with self.assertRaises(OSError):
                B.save_json(self.path, {"version": 2})
        self.assertEqual(B.load_json(self.path, None), {"version": 1})

    def test_echec_du_remplacement_garde_l_ancien_fichier(self):
        B.save_json(self.path, {"version": 1})
        with mock.patch.object(B.os, "replace", side_effect=OSError("fichier verrouillé")):
            with self.assertRaises(OSError):
                B.save_json(self.path, {"version": 2})
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"version": 1})


class FichierIllisible(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(dir=WORK)
        self.path = os.path.join(self.dossier, "memory.json")

    def test_fichier_absent_donne_la_valeur_par_defaut(self):
        self.assertEqual(B.load_json(self.path, {"vide": True}), {"vide": True})

    def test_fichier_corrompu_est_mis_de_cote_pas_ecrase(self):
        abime = '{"memories": ["un souvenir précieux", "coupé en plein mil'
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(abime)

        self.assertEqual(B.load_json(self.path, {"vide": True}), {"vide": True})

        # Le fichier abîmé n'est plus à sa place : la prochaine sauvegarde ne l'écrasera pas…
        self.assertFalse(os.path.exists(self.path))
        # …et son contenu est conservé à côté, intact, pour être réparé.
        gardes = [f for f in os.listdir(self.dossier) if f.startswith("memory.json.corrompu-")]
        self.assertEqual(len(gardes), 1)
        with open(os.path.join(self.dossier, gardes[0]), encoding="utf-8") as f:
            self.assertEqual(f.read(), abime)


class Historique(unittest.IsolatedAsyncioTestCase):
    """history.json n'est chargé qu'à la connexion (on_ready). Tant qu'il ne l'est pas, on ne
    l'écrit pas — sinon un démarrage raté l'écrasait par un historique vide."""

    def setUp(self):
        dossier = tempfile.mkdtemp(dir=WORK)
        self.path = os.path.join(dossier, "history.json")
        self.contenu = {"threads": {"42": [{"role": "user", "content": "bonjour"}]},
                        "summaries": {"42": "un résumé"}}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.contenu, f)
        for nom, valeur in (("HISTORY_FILE", self.path), ("_histories_loaded", False),
                            ("_histories_dirty", False), ("conversations", {}), ("summaries", {})):
            p = mock.patch.object(B, nom, valeur)
            p.start()
            self.addCleanup(p.stop)

    def _sur_disque(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    async def test_rien_n_est_ecrit_avant_le_chargement(self):
        B.save_histories()
        await B.flush_histories(force=True)
        self.assertEqual(self._sur_disque(), self.contenu)

    async def test_charge_puis_sauvegarde(self):
        B.load_histories()
        self.assertIn(42, B.conversations)
        self.assertEqual(B.summaries, {42: "un résumé"})
        B.conversations[7] = [{"role": "user", "content": "nouveau"}]
        B.save_histories()
        self.assertEqual(set(self._sur_disque()["threads"]), {"42", "7"})

    async def test_une_reconnexion_ne_recharge_pas_le_fichier(self):
        B.load_histories()
        B.conversations[7] = [{"role": "user", "content": "pas encore enregistré"}]
        B.load_histories()                       # on_ready se redéclenche à chaque reconnexion
        self.assertIn(7, B.conversations)


if __name__ == "__main__":
    unittest.main()
