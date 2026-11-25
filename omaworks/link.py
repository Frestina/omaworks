"""Build the link that opens the report form with fields filled in."""

from urllib.parse import quote

BASE_URL = "https://github.com/Frestina/omaworks/issues/new"
TEMPLATE = "report.yml"

# GitHub documents no number: a URL over its server limit gets "414 URI Too
# Long". 8192 bytes is a common server limit for a request line, so stay well
# under it. See SPEC.md, "Prefilling the form".
MAX_LINK_LENGTH = 6000

RESULTS = ("Works", "Works with problems", "Broken")


class LinkError(ValueError):
    """The link cannot be built."""


class LinkTooLong(LinkError):
    """The link is longer than GitHub accepts."""


def build_report_link(plugin, omarchy, commit, result=None, what=None, errors=None):
    """Return the report-form link.

    plugin, omarchy and commit are required. result, what and errors are
    optional and left out of the link when empty. result is the option text.
    """
    params = [("template", TEMPLATE)]
    for name, value in (("plugin", plugin), ("omarchy", omarchy), ("commit", commit)):
        if not value or not value.strip():
            raise LinkError(f"{name} is required")
        params.append((name, value))
    if result:
        if result not in RESULTS:
            raise LinkError(f"result must be one of: {', '.join(RESULTS)}")
        params.append(("result", result))
    for name, value in (("what", what), ("errors", errors)):
        if value and value.strip():
            params.append((name, value))
    query = "&".join(f"{k}={quote(v, safe='')}" for k, v in params)
    link = f"{BASE_URL}?{query}"
    if len(link) > MAX_LINK_LENGTH:
        raise LinkTooLong(
            f"link is {len(link)} characters, the limit is {MAX_LINK_LENGTH}"
        )
    return link
