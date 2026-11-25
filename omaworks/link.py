"""Build the link that opens the report form with fields filled in."""

from urllib.parse import quote

BASE_URL = "https://github.com/Frestina/omaworks/issues/new"
TEMPLATE = "report.yml"

# Longer links fail for reporters who are not signed in. See SPEC.md,
# "Link length".
MAX_LINK_LENGTH = 3500


class LinkError(ValueError):
    """The link cannot be built."""


class LinkTooLong(LinkError):
    """The link is longer than GitHub accepts."""


def build_form_link():
    """The report form with nothing filled in."""
    return f"{BASE_URL}?template={TEMPLATE}"


def _clean(value):
    return value.strip() if value else ""


def build_report_link(plugin, omarchy=None, commit=None):
    """Return the report-form link.

    Only the fixed fields go in it: the plugin, the Omarchy version and the
    plugin's commit, and the title. GitHub locks every field a link fills in,
    so What happens and Error lines never go in it. The reporter pastes them.
    See SPEC.md, "Only the fixed fields go in the link".

    Only plugin is required. The other fields are left out when empty. Every
    value is stripped of surrounding whitespace. The result is not in the link:
    GitHub does not prefill a dropdown. The title is "<plugin> on <omarchy>",
    or just the plugin without a version.
    """
    plugin, omarchy, commit = (_clean(v) for v in (plugin, omarchy, commit))
    if not plugin:
        raise LinkError("plugin is required")
    title = f"{plugin} on {omarchy}" if omarchy else plugin
    params = [("template", TEMPLATE), ("title", title), ("plugin", plugin)]
    for name, value in (("omarchy", omarchy), ("commit", commit)):
        if value:
            params.append((name, value))
    query = "&".join(f"{k}={quote(v, safe='')}" for k, v in params)
    link = f"{BASE_URL}?{query}"
    if len(link) > MAX_LINK_LENGTH:
        raise LinkTooLong(
            f"link is {len(link)} characters, the limit is {MAX_LINK_LENGTH}"
        )
    return link
