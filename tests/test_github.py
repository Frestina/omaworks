import io
import json
import unittest
import urllib.error
import urllib.request

from omaworks import github
from omaworks.check import SourceError, label
from omaworks.github import CATALOG_URL, GitHub


class FakeResponse:
    def __init__(self, status, data):
        self.status = status
        self._data = io.BytesIO(data)

    def read(self, n=-1):
        return self._data.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    """Answers requests from a list of (status, JSON) replies. No network."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        status, payload = self.replies.pop(0)
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        if status >= 400:
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(data))
        return FakeResponse(status, data)


def client(*replies):
    opener = FakeOpener(*replies)
    return GitHub("secret-token", opener=opener), opener


class GitHubTest(unittest.TestCase):
    def test_catalog_is_fetched_without_the_token(self):
        gh, opener = client((200, {"plugins": [{"id": "example.sky-clock"}]}))
        self.assertEqual(gh.catalog(), [{"id": "example.sky-clock"}])
        request = opener.requests[0]
        self.assertEqual(request.full_url, CATALOG_URL)
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.get_header("Authorization"))

    def test_bad_catalog_raises(self):
        for reply in ((200, b"not json"), (200, {"items": []}), (503, {})):
            with self.subTest(reply=reply):
                gh, _ = client(reply)
                with self.assertRaises(SourceError):
                    gh.catalog()

    def test_api_requests_carry_the_token(self):
        gh, opener = client((200, {"ref": "refs/tags/v4.5.0"}))
        self.assertTrue(gh.omarchy_tag_exists("v4.5.0"))
        request = opener.requests[0]
        self.assertEqual(
            request.full_url, "https://api.github.com/repos/omacom/omarchy/git/ref/tags/v4.5.0"
        )
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")

    def test_missing_tag_is_false_and_errors_raise(self):
        gh, _ = client((404, {"message": "Not Found"}))
        self.assertFalse(gh.omarchy_tag_exists("v9.9.9"))
        gh, _ = client((500, {}))
        with self.assertRaises(SourceError):
            gh.omarchy_tag_exists("v4.5.0")

    def test_repo_lookup(self):
        gh, opener = client((200, {"full_name": "Example-Dev/Weather-Strip", "private": False}))
        self.assertEqual(gh.github_repo("example-dev", "weather-strip"), "Example-Dev/Weather-Strip")
        self.assertEqual(
            opener.requests[0].full_url, "https://api.github.com/repos/example-dev/weather-strip"
        )
        self.assertEqual(opener.requests[0].get_method(), "GET")
        for reply in ((404, {}), (451, {}), (200, {"full_name": "a/b", "private": True})):
            gh, _ = client(reply)
            self.assertIsNone(gh.github_repo("a", "b"))

    def test_label_names_are_encoded_in_paths(self):
        gh, opener = client((204, b""))
        gh.remove_label("example-owner/omaworks", 7, "repo:example-dev/sky~1a2b3c")
        self.assertEqual(
            opener.requests[0].full_url,
            "https://api.github.com/repos/example-owner/omaworks/issues/7/labels/"
            "repo%3Aexample-dev%2Fsky~1a2b3c",
        )
        self.assertEqual(opener.requests[0].get_method(), "DELETE")

    def test_existing_label_is_not_an_error(self):
        gh, opener = client((422, {"message": "already_exists"}))
        gh.ensure_label("example-owner/omaworks", label("plugin:", "example.sky-clock", "d", "1d76db"))
        sent = json.loads(opener.requests[0].data)
        self.assertEqual(sent, {"name": "plugin:example.sky-clock", "color": "1d76db", "description": "d"})

    def test_comments_follow_pages(self):
        first = [{"id": n} for n in range(100)]
        gh, opener = client((200, first), (200, [{"id": 100}]))
        self.assertEqual(len(gh.comments("example-owner/omaworks", 7)), 101)
        self.assertTrue(opener.requests[1].full_url.endswith("?per_page=100&page=2"))

    def test_oversized_reply_raises(self):
        gh, _ = client((200, b"[" + b" " * github.MAX_API_BYTES + b"]"))
        with self.assertRaises(SourceError):
            gh.get_issue("example-owner/omaworks", 7)


class RedirectTest(unittest.TestCase):
    def setUp(self):
        self.handler = github._SameHostRedirects()
        self.request = urllib.request.Request("https://api.github.com/repos/a/b")
        self.request.add_header("Authorization", "Bearer secret-token")

    def redirect(self, url):
        return self.handler.redirect_request(self.request, None, 301, "Moved", {}, url)

    def test_same_host_is_followed(self):
        new = self.redirect("https://api.github.com/repositories/1")
        self.assertEqual(new.full_url, "https://api.github.com/repositories/1")

    def test_other_host_or_plain_http_is_refused(self):
        for url in ("https://example.invalid/x", "http://api.github.com/x"):
            with self.subTest(url=url):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    self.redirect(url)
                caught.exception.close()


if __name__ == "__main__":
    unittest.main()
