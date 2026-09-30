"""textutils : fonctions de texte pures (aucune dépendance au bot)."""
import unittest

import support  # noqa: F401  (ajoute la racine du dépôt au chemin d'import)
import textutils as T


class Normalisation(unittest.TestCase):
    def test_fold_retire_les_accents_en_gardant_la_longueur(self):
        self.assertEqual(T._fold("Maël34 à l'Écoute"), "mael34 a l'ecoute")
        self.assertEqual(len(T._fold("Téowyne")), len("Téowyne"))

    def test_words_ignore_accents_mots_courts_et_mots_outils(self):
        self.assertEqual(T._words("Avec les Linnorms du Nord, très vite"), {"linnorms", "nord", "vite"})

    def test_stem_rapproche_les_conjugaisons(self):
        racines = {T._stem(w) for w in ("jouer", "jouais", "jouait", "jouaient")}
        self.assertEqual(racines, {"jou"})
        self.assertEqual(T._stem("chat"), "chat")          # jamais moins de 3 lettres de racine


class Similarite(unittest.TestCase):
    def test_meme_texte_a_la_casse_et_aux_espaces_pres(self):
        self.assertTrue(T._too_similar("Il aime  les échecs", "il aime les échecs"))

    def test_textes_sans_rapport(self):
        self.assertFalse(T._too_similar("Il aime les échecs", "Elle travaille à Lyon"))
        self.assertEqual(T._similarity("", "quelque chose"), 0.0)

    def test_similarity_est_un_ratio(self):
        self.assertEqual(T._similarity("dragon rouge", "dragon rouge"), 1.0)
        self.assertAlmostEqual(T._similarity("dragon rouge ancien", "dragon rouge jeune"), 0.5)


class Decoupe(unittest.TestCase):
    def test_texte_court_intact(self):
        self.assertEqual(T.smart_split("salut"), ["salut"])

    def test_decoupe_sur_les_sauts_de_ligne_sans_rien_perdre(self):
        texte = "\n".join(f"ligne {i} " + "x" * 50 for i in range(100))
        morceaux = T.smart_split(texte, limit=500)
        self.assertTrue(all(len(m) <= 500 for m in morceaux))
        self.assertEqual("\n".join(morceaux), texte)

    def test_une_ligne_geante_est_coupee_durement(self):
        morceaux = T.smart_split("a" * 4500, limit=2000)
        self.assertEqual([len(m) for m in morceaux], [2000, 2000, 500])


class JsonTolerant(unittest.TestCase):
    def test_json_propre(self):
        self.assertEqual(T._parse_json_loose('{"a": 1}'), {"a": 1})

    def test_json_dans_des_balises_markdown(self):
        self.assertEqual(T._parse_json_loose('```json\n{"humeur": "taquine"}\n```'), {"humeur": "taquine"})

    def test_json_entoure_de_texte(self):
        self.assertEqual(T._parse_json_loose('Voici : [1, 2, 3] — terminé.'), [1, 2, 3])

    def test_illisible_ou_vide(self):
        self.assertIsNone(T._parse_json_loose("pas du json"))
        self.assertIsNone(T._parse_json_loose(""))


if __name__ == "__main__":
    unittest.main()
