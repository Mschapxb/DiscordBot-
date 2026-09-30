"""Anti-SSRF : le bot ne lit jamais une adresse de son propre réseau, même déguisée,
même derrière un nom de domaine, même au bout d'une redirection."""
import asyncio
import types
import unittest
from unittest import mock

import aiohttp

from support import load_bot

B = load_bot()


class SafeUrl(unittest.TestCase):
    def test_adresses_publiques_acceptees(self):
        for url in ("https://orbis-naturae.forumactif.com/t1-sujet",
                    "http://example.org/page?x=1",
                    "https://8.8.8.8/",
                    "https://[2001:4860:4860::8888]/"):
            with self.subTest(url=url):
                self.assertEqual(B._safe_url(url), url)

    def test_autres_protocoles_refuses(self):
        for url in ("ftp://example.org/x", "file:///etc/passwd", "javascript:alert(1)", "example.org", ""):
            with self.subTest(url=url):
                self.assertIsNone(B._safe_url(url))

    def test_adresses_internes_refusees(self):
        for url in ("http://localhost:10000/admin", "http://LOCALHOST/", "http://app.localhost/",
                    "http://127.0.0.1/", "http://10.0.0.5/", "http://192.168.1.1/", "http://172.20.0.1/",
                    "http://169.254.169.254/latest/meta-data/",      # métadonnées cloud
                    "http://100.64.0.1/", "http://0.0.0.0/", "http://224.0.0.1/",
                    "http://[::1]/", "http://[fd00::1]/", "http://[fe80::1]/",
                    "http://[::ffff:127.0.0.1]/"):
            with self.subTest(url=url):
                self.assertIsNone(B._safe_url(url))

    def test_ip_deguisees_refusees(self):
        # Toutes ces écritures désignent 127.0.0.1 pour le système.
        for url in ("http://2130706433/", "http://0x7f000001/", "http://127.1/",
                    "http://0177.0.0.1/", "http://0x7f.0.0.1/"):
            with self.subTest(url=url):
                self.assertIsNone(B._safe_url(url))


class ResolveurPublic(unittest.IsolatedAsyncioTestCase):
    def _resolveur(self, reponses):
        r = B._PublicOnlyResolver()

        async def faux(host, port=0, family=0):
            return [{"hostname": host, "host": ip, "port": port} for ip in reponses[host]]
        r._inner = types.SimpleNamespace(resolve=faux)
        return r

    async def test_nom_qui_pointe_vers_le_reseau_interne(self):
        r = self._resolveur({"piege.example": ["10.0.0.5"], "meta.example": ["169.254.169.254"]})
        for nom in ("piege.example", "meta.example"):
            with self.subTest(nom=nom), self.assertRaises(B._AdresseInterne):
                await r.resolve(nom, 80)

    async def test_seules_les_adresses_publiques_sont_rendues(self):
        r = self._resolveur({"mixte.example": ["93.184.216.34", "127.0.0.1"]})
        infos = await r.resolve("mixte.example", 443)
        self.assertEqual([i["host"] for i in infos], ["93.184.216.34"])

    async def test_le_reader_proxy_configure_reste_joignable_en_local(self):
        with mock.patch.object(B, "FORUM_READER_PROXY", "http://reader.maison:3000/"):
            r = self._resolveur({"reader.maison": ["192.168.1.20"]})
        infos = await r.resolve("reader.maison", 3000)
        self.assertEqual([i["host"] for i in infos], ["192.168.1.20"])


class _Reponse:
    def __init__(self, url, status=200, headers=None, corps=b"<html><title>T</title>ok</html>"):
        self.url, self.status = url, status
        self.headers = {"Content-Type": "text/html", **(headers or {})}
        self.content = types.SimpleNamespace(read=mock.AsyncMock(return_value=corps))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _Session:
    """Fausse session : rejoue un scénario {url: réponse} et note chaque URL demandée."""

    def __init__(self, scenario):
        self.scenario, self.appels = scenario, []

    def get(self, url, **kw):
        assert kw.get("allow_redirects") is False, "les redirections doivent être suivies à la main"
        self.appels.append(url)
        rep = self.scenario[url]
        if isinstance(rep, Exception):
            raise rep
        return rep


class Redirections(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = mock.patch.object(B, "_fetch_via_reader", mock.AsyncMock(return_value=None))
        self.reader = p.start()
        self.addCleanup(p.stop)

    async def test_adresse_interne_directe_aucune_requete(self):
        s = _Session({})
        self.assertIsNone(await B._fetch_raw("http://127.0.0.1:10000/admin", session=s))
        self.assertEqual(s.appels, [])

    async def test_redirection_vers_le_reseau_interne_refusee(self):
        for cible in ("http://127.0.0.1:10000/admin/api/state", "http://169.254.169.254/",
                      "http://2130706433/", "file:///etc/passwd"):
            with self.subTest(cible=cible):
                depart = "https://site-public.example/article"
                s = _Session({depart: _Reponse(depart, 302, {"Location": cible})})
                page = await B._fetch_raw(depart, session=s)
                self.assertIn("redirection refusée", page["error"])
                self.assertEqual(s.appels, [depart])          # la cible n'est JAMAIS demandée
        self.reader.assert_not_called()

    async def test_redirection_publique_suivie(self):
        depart, arrivee = "http://example.org/vieux", "https://example.org/nouveau"
        s = _Session({depart: _Reponse(depart, 301, {"Location": "https://example.org/nouveau"}),
                      arrivee: _Reponse(arrivee)})
        page = await B._fetch_raw(depart, session=s)
        self.assertEqual(s.appels, [depart, arrivee])
        self.assertEqual(page["url"], arrivee)
        self.assertIn("ok", page["html"])

    async def test_redirection_relative(self):
        depart, arrivee = "https://example.org/a/b", "https://example.org/c"
        s = _Session({depart: _Reponse(depart, 302, {"Location": "/c"}), arrivee: _Reponse(arrivee)})
        self.assertEqual((await B._fetch_raw(depart, session=s))["url"], arrivee)

    async def test_boucle_de_redirections_bornee(self):
        url = "https://example.org/boucle"
        s = _Session({url: _Reponse(url, 302, {"Location": url})})
        page = await B._fetch_raw(url, session=s)
        self.assertEqual(page["error"], "trop de redirections")
        self.assertEqual(len(s.appels), B.WEB_MAX_REDIRECTS + 1)

    async def test_nom_resolu_vers_l_interne_ni_relance_ni_reader_proxy(self):
        url = "https://piege.example/"
        cle = types.SimpleNamespace(host="piege.example", port=443, ssl=True, is_ssl=True)
        erreur = aiohttp.ClientConnectorError(cle, B._AdresseInterne("adresse interne bloquée"))
        s = _Session({url: erreur})
        page = await B._fetch_raw(url, session=s)
        self.assertEqual(page["error"], "adresse interne refusée")
        self.assertEqual(s.appels, [url])
        self.reader.assert_not_called()


class LiensConfiesAYtDlp(unittest.IsolatedAsyncioTestCase):
    def _dns(self, ip):
        boucle = asyncio.get_running_loop()
        return mock.patch.object(boucle, "getaddrinfo",
                                 mock.AsyncMock(return_value=[(2, 1, 6, "", (ip, 0))]))

    async def test_url_publique(self):
        with self._dns("93.184.216.34"):
            self.assertTrue(await B.url_publique("https://example.org/son.mp3"))
        with self._dns("10.0.0.7"):
            self.assertFalse(await B.url_publique("https://intranet.example/son.mp3"))
        self.assertFalse(await B.url_publique("http://127.0.0.1:10000/admin"))

    async def test_jouer_refuse_un_lien_interne_sans_appeler_yt_dlp(self):
        with mock.patch.object(B, "_extract", mock.AsyncMock()) as extraction:
            with self.assertRaises(RuntimeError):
                await B.fetch_track("http://127.0.0.1:10000/admin", "Joueur")
            extraction.assert_not_called()


if __name__ == "__main__":
    unittest.main()
