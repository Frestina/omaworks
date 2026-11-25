"""Talk to GitHub's REST API and fetch the catalog, with urllib only.

The token goes only to api.github.com, never to the catalog's host, and a
redirect to another host is refused. Values from a report reach a URL only
after omaworks.check has matched them against a strict pattern, and they are
percent-encoded even then.
"""

import json
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit

from omaworks.check import SourceError

API = "https://api.github.com"
CATALOG_URL = "https://plugins.omarchy.org/catalog.json"
OMARCHY_REPO = "omacom/omarchy"
USER_AGENT = "omaworks-check"

# The catalog was 18 MB in November 2026. Anything far bigger is not it.
MAX_CATALOG_BYTES = 200 * 1024 * 1024
MAX_API_BYTES = 10 * 1024 * 1024


class _SameHostRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to the same https host, so the token stays put."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urlsplit(req.full_url), urlsplit(newurl)
        if new.scheme != "https" or new.hostname != old.hostname:
            raise urllib.error.HTTPError(
                newurl, code, "redirect to another host refused", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(request, limit, opener=None):
    opener = opener or urllib.request.build_opener(_SameHostRedirects)
    with opener.open(request, timeout=60) as response:
        status = response.status
        data = response.read(limit + 1)
    if len(data) > limit:
        raise SourceError(f"{request.full_url} sent more than {limit} bytes")
    return status, data


class GitHub:
    """A small REST client for one token."""

    def __init__(self, token, opener=None):
        self.token = token
        self.opener = opener

    def request(self, method, path, data=None, allow=()):
        """Return (status, parsed JSON or None).

        A status in allow is returned rather than raised. Any other error
        raises SourceError.
        """
        url = f"{API}{path}"
        body = None if data is None else json.dumps(data).encode()
        request = urllib.request.Request(url, data=body, method=method)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        request.add_header("User-Agent", USER_AGENT)
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            status, raw = _open(request, MAX_API_BYTES, self.opener)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code in allow:
                return error.code, None
            raise SourceError(f"{method} {path} failed: HTTP {error.code}") from None
        except (urllib.error.URLError, OSError) as error:
            raise SourceError(f"{method} {path} failed: {error}") from None
        try:
            return status, json.loads(raw) if raw else None
        except ValueError:
            raise SourceError(f"{method} {path} sent something that isn't JSON") from None

    def get_pages(self, path):
        """Every item of a paged list."""
        items = []
        page = 1
        while True:
            sep = "&" if "?" in path else "?"
            _, batch = self.request("GET", f"{path}{sep}per_page=100&page={page}")
            if not isinstance(batch, list):
                raise SourceError(f"GET {path} did not send a list")
            items += batch
            if len(batch) < 100:
                return items
            page += 1

    # Reading: the sources omaworks.check uses.

    def omarchy_tag_exists(self, tag):
        status, _ = self.request(
            "GET", f"/repos/{OMARCHY_REPO}/git/ref/tags/{quote(tag, safe='')}", allow=(404,)
        )
        return status == 200

    def github_repo(self, owner, name):
        status, data = self.request(
            "GET", f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}", allow=(404, 451)
        )
        if status != 200 or not isinstance(data, dict) or data.get("private"):
            return None
        full_name = data.get("full_name")
        return full_name if isinstance(full_name, str) else None

    def catalog(self):
        """The catalog's plugins list. Sent without the token."""
        request = urllib.request.Request(CATALOG_URL)
        request.add_header("User-Agent", USER_AGENT)
        try:
            _, raw = _open(request, MAX_CATALOG_BYTES, self.opener)
            data = json.loads(raw)
        except urllib.error.HTTPError as error:
            error.close()
            raise SourceError(f"the catalog could not be read: HTTP {error.code}") from None
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise SourceError(f"the catalog could not be read: {error}") from None
        if not isinstance(data, dict) or "plugins" not in data:
            raise SourceError("the catalog has no plugins list")
        return data["plugins"]

    # The issue being checked.

    def get_issue(self, repo, number):
        _, data = self.request("GET", f"/repos/{repo}/issues/{number}")
        return data

    def comments(self, repo, number):
        return self.get_pages(f"/repos/{repo}/issues/{number}/comments")

    def create_comment(self, repo, number, body):
        self.request("POST", f"/repos/{repo}/issues/{number}/comments", {"body": body})

    def edit_comment(self, repo, comment_id, body):
        self.request("PATCH", f"/repos/{repo}/issues/comments/{comment_id}", {"body": body})

    def ensure_label(self, repo, label):
        """Create the label unless it exists. 422 means it already does."""
        self.request(
            "POST",
            f"/repos/{repo}/labels",
            {"name": label.name, "color": label.color, "description": label.description},
            allow=(422,),
        )

    def add_labels(self, repo, number, names):
        self.request("POST", f"/repos/{repo}/issues/{number}/labels", {"labels": names})

    def remove_label(self, repo, number, name):
        self.request(
            "DELETE",
            f"/repos/{repo}/issues/{number}/labels/{quote(name, safe='')}",
            allow=(404,),
        )
