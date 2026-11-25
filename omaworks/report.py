"""Read a report issue's body into its six fields.

GitHub turns the issue form into Markdown: each field is a line "### <Label>",
a blank line, then the value. An empty optional field reads "_No response_".
The "Error lines" field is wrapped in a ```text fence.

The body is untrusted text written by a stranger. This module only splits it
into strings. Nothing here runs, renders or follows any of it.
"""

# Field ID and the heading GitHub writes for it, in form order. They match
# .github/ISSUE_TEMPLATE/report.yml.
FIELDS = (
    ("plugin", "Plugin"),
    ("omarchy", "Omarchy version"),
    ("commit", "Plugin commit"),
    ("result", "Result"),
    ("what", "What happens"),
    ("errors", "Error lines"),
)

LABELS = dict(FIELDS)

NO_RESPONSE = "_No response_"


def _strip_fence(value):
    """Remove the ```text fence GitHub puts around a render: text field."""
    lines = value.split("\n")
    if (
        len(lines) >= 2
        and lines[0].strip() in ("```text", "```")
        and lines[-1].strip() == "```"
    ):
        return "\n".join(lines[1:-1]).strip()
    return value


def parse_body(body):
    """Return {field id: value} for the six fields.

    A field whose heading is missing is None. An empty field, or one that
    reads "_No response_", is "". Headings are looked for in form order, each
    after the one before, so a heading typed inside a later field's text
    cannot replace an earlier field.
    """
    if not isinstance(body, str):
        body = ""
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    starts = {}
    pos = 0
    for field, label in FIELDS:
        heading = f"### {label}"
        for i in range(pos, len(lines)):
            if lines[i].rstrip() == heading:
                starts[field] = i
                pos = i + 1
                break
    found = sorted(starts.items(), key=lambda item: item[1])
    values = {field: None for field, _ in FIELDS}
    for n, (field, start) in enumerate(found):
        end = found[n + 1][1] if n + 1 < len(found) else len(lines)
        value = "\n".join(lines[start + 1 : end]).strip()
        if value == NO_RESPONSE:
            value = ""
        if field == "errors":
            value = _strip_fence(value)
        values[field] = value
    return values
