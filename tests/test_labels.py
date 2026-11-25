import io
import json
import os
import re
import unittest
import urllib.error
from urllib.parse import unquote, urlsplit

from omaworks import labels
from omaworks.check import MAX_DESCRIPTION, MAX_LABEL, NEEDS_FIX_LABEL, is_owned
from omaworks.count import FROM_ISSUE, REPORT, SKIP
from tests.test_github import FakeResponse

REPO = "example-owner/omaworks"
# Built from parts, so no whole token-like value is written down.
TOKEN = "ghp_" + "Zx9" * 12
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LabelServer:
    """GitHub's label endpoints for one repo, in memory. No network."""

    def __init__(self, existing=(), fail_on=None):
        self.labels = {item["name"].lower(): dict(item) for item in existing}
        self.requests = []
        self.fail_on = fail_on

    def open(self, request, timeout=None):
        method = request.get_method()
        path = urlsplit(request.full_url).path
        self.requests.append((method, path, request))
        if self.fail_on == method:
            raise urllib.error.HTTPError(request.full_url, 500, "error", {}, io.BytesIO(b"{}"))
        prefix = f"/repos/{REPO}/labels"
        body = json.loads(request.data) if request.data else None
        if method == "POST" and path == prefix:
            self.labels[body["name"].lower()] = body
            return self.reply(201, body)
        name = unquote(path[len(prefix) + 1:]).lower()
        if name not in self.labels:
            return self.reply(404, {"message": "Not Found"}, request)
        if method == "GET":
            return self.reply(200, self.labels[name])
        if method == "PATCH":
            item = self.labels.pop(name)
            item.update(name=body["new_name"], color=body["color"], description=body["description"])
            self.labels[item["name"].lower()] = item
            return self.reply(200, item)
        raise AssertionError(f"unexpected {method} {path}")

    def reply(self, status, payload, request=None):
        data = json.dumps(payload).encode()
        if status >= 400:
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(data))
        return FakeResponse(status, data)

    def writes(self):
        return [(m, p) for m, p, _ in self.requests if m != "GET"]


def run_main(server, *argv, env=None):
    out, err = io.StringIO(), io.StringIO()
    env = {"GITHUB_TOKEN": TOKEN} if env is None else env
    code = labels.main(list(argv), environ=env, out=out, err=err, opener=server)
    return code, out.getvalue(), err.getvalue()


class LabelListTest(unittest.TestCase):
    def test_the_six_labels(self):
        self.assertEqual(
            [item.name for item in labels.LABELS],
            ["report", "needs-fix", "spam", "needs-look", "from-issue", "test"],
        )

    def test_names_match_what_the_check_and_the_count_use(self):
        names = {item.name for item in labels.LABELS}
        self.assertIn(REPORT, names)
        self.assertIn(FROM_ISSUE, names)
        self.assertLessEqual(SKIP, names)
        self.assertIn(NEEDS_FIX_LABEL, labels.LABELS)

    def test_only_needs_fix_is_owned_by_the_check(self):
        owned = [item.name for item in labels.LABELS if is_owned(item.name)]
        self.assertEqual(owned, ["needs-fix"])

    def test_the_spec_lists_the_same_labels(self):
        with open(os.path.join(ROOT, "SPEC.md"), encoding="utf-8") as f:
            spec = f.read()
        for item in labels.LABELS:
            with self.subTest(label=item.name):
                self.assertIn(
                    f"| `{item.name}` | `{item.color}` | {item.description} |", spec
                )

    def test_github_accepts_them(self):
        for item in labels.LABELS:
            with self.subTest(label=item.name):
                self.assertRegex(item.color, r"\A[0-9a-f]{6}\Z")
                self.assertLessEqual(len(item.name), MAX_LABEL)
                self.assertTrue(item.description)
                self.assertLessEqual(len(item.description), MAX_DESCRIPTION)


class LabelScriptTest(unittest.TestCase):
    def test_creates_the_missing_labels(self):
        server = LabelServer()
        code, out, err = run_main(server, REPO)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(len(server.writes()), 6)
        self.assertTrue(all(m == "POST" for m, _ in server.writes()))
        for item in labels.LABELS:
            self.assertEqual(
                server.labels[item.name],
                {"name": item.name, "color": item.color, "description": item.description},
            )
        self.assertIn("created        needs-look", out)

    def test_a_second_run_changes_nothing(self):
        server = LabelServer()
        run_main(server, REPO)
        server.requests.clear()
        code, out, _ = run_main(server, REPO)
        self.assertEqual(code, 0)
        self.assertEqual(server.writes(), [])
        self.assertEqual(out.count("ok "), 6)

    def test_fixes_colour_text_and_case_and_keeps_the_rest(self):
        server = LabelServer(existing=[
            {"name": "Spam", "color": "FFFFFF", "description": "old"},
            {"name": "test", "color": "EDEDED", "description": labels.LABELS[5].description},
            {"name": "plugin:example.sky-clock", "color": "1d76db", "description": "x"},
        ])
        code, out, _ = run_main(server, REPO)
        self.assertEqual(code, 0)
        self.assertIn(("PATCH", f"/repos/{REPO}/labels/Spam"), server.writes())
        self.assertIn("updated        spam (was Spam)", out)
        self.assertIn("ok             test", out)  # colour case doesn't matter
        self.assertNotIn("spam", [p.rsplit("/", 1)[-1] for m, p in server.writes() if m == "POST"])
        self.assertEqual(server.labels["spam"]["name"], "spam")
        self.assertEqual(server.labels["plugin:example.sky-clock"]["description"], "x")
        touched = {unquote(p.rsplit("/", 1)[-1]) for _, p, _ in server.requests}
        self.assertNotIn("plugin:example.sky-clock", touched)

    def test_dry_run_only_reads(self):
        server = LabelServer(existing=[{"name": "report", "color": "000000", "description": ""}])
        code, out, _ = run_main(server, "--dry-run", REPO)
        self.assertEqual(code, 0)
        self.assertEqual(server.writes(), [])
        self.assertIn("would update   report", out)
        self.assertIn("would create   needs-look", out)

    def test_dry_run_needs_no_token(self):
        server = LabelServer()
        code, _, _ = run_main(server, "--dry-run", REPO, env={})
        self.assertEqual(code, 0)
        self.assertIsNone(server.requests[0][2].get_header("Authorization"))

    def test_a_real_run_needs_a_token(self):
        server = LabelServer()
        code, _, err = run_main(server, REPO, env={})
        self.assertEqual(code, 2)
        self.assertIn("GITHUB_TOKEN", err)
        self.assertEqual(server.requests, [])

    def test_the_token_goes_only_to_the_api_and_is_never_printed(self):
        for server in (LabelServer(), LabelServer(fail_on="POST"), LabelServer(fail_on="GET")):
            with self.subTest(fail_on=server.fail_on):
                code, out, err = run_main(server, REPO)
                self.assertNotIn(TOKEN, out + err)
                self.assertNotIn(TOKEN[4:], out + err)
                for _, _, request in server.requests:
                    self.assertTrue(request.full_url.startswith("https://api.github.com/"))
                    self.assertEqual(request.get_header("Authorization"), f"Bearer {TOKEN}")
                if server.fail_on:
                    self.assertEqual(code, 1)
                    self.assertTrue(err.startswith("omaworks: "))

    def test_a_failed_read_writes_nothing(self):
        server = LabelServer(fail_on="GET")
        run_main(server, REPO)
        self.assertEqual(server.writes(), [])

    def test_a_bad_repo_is_refused_before_any_request(self):
        for repo in ("omaworks", "a/b/c", "../x", "owner/repo?x=1"):
            with self.subTest(repo=repo):
                server = LabelServer()
                code, _, err = run_main(server, repo)
                self.assertEqual(code, 2)
                self.assertEqual(server.requests, [])
                self.assertTrue(re.match(r"omaworks: ", err))


if __name__ == "__main__":
    unittest.main()
