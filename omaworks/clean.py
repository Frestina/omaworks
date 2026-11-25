"""Remove personal details from log lines before they go into a draft.

See SPEC.md, "What must never happen", rule 3, and "The shortcut". Removing
too much is safe. Removing too little is not, so when in doubt a value goes.

What is removed, in this order:

- terminal colour codes;
- the home path, which becomes "~", and any other /home/<name>;
- email addresses;
- the hostname, which often holds the username;
- the username, as a whole word;
- anything that looks like a token or a secret.

Text matched by keep, such as the plugin's own ID and its files' paths, is
never changed. A clone made with `omarchy plugin clone` has the username in
its ID, and the ID is in the report's Plugin field anyway.
"""

import re

USER = "<user>"
HOST = "<host>"
EMAIL = "<email>"
REMOVED = "<removed>"

# CSI sequences such as ESC[33m, OSC sequences such as ESC]8;;...ESC\, and any
# other escape left over.
ANSI_RE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?"
    r"|\x1b[@-_]?"
)
# Other control characters, except tab.
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

OTHER_HOME_RE = re.compile(r"/home/(?!<user>)[A-Za-z0-9._-]+")

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")

# A name, then : or =, then a value: password=..., "token": "...".
SECRET_RE = re.compile(
    r"(?i)((?:token|secret|password|passwd|api[_-]?key|key|auth|cookie|credentials?)"
    r"[\"']?\s*[:=]\s*[\"']?)[^\s\"',;&]+"
)
BEARER_RE = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
# Tokens with a known prefix, kept short: GitHub, GitLab, Slack, AWS, OpenAI
# and Anthropic style keys.
PREFIXED_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}"
    r"|glpat-[A-Za-z0-9_-]{16,}|xox[abposr]-[A-Za-z0-9-]{10,}"
    r"|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{16,})"
)
# A long run of letters and digits, such as a hash or an encoded key.
LONG_RUN_RE = re.compile(r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/_-]{32,}={0,2}(?![A-Za-z0-9+/=_-])")


def strip_colours(text):
    """Text without terminal colour codes or other control characters."""
    return CONTROL_RE.sub("", ANSI_RE.sub("", text))


def _word(value):
    """A pattern for value as a whole word, in any case."""
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", re.IGNORECASE
    )


def _looks_like_token(run):
    # A path such as /usr/lib/qt6/qml is a long run too. Paths are cleaned by
    # the home rules instead.
    if run.startswith("/") or "//" in run:
        return False
    body = run.rstrip("=")
    if re.fullmatch(r"[0-9a-fA-F]+", body):
        return True
    return bool(re.search(r"[0-9]", body) and re.search(r"[A-Za-z]", body))


def _tokens(text):
    text = PREFIXED_RE.sub(REMOVED, text)
    text = BEARER_RE.sub(lambda m: f"{m.group(1)} {REMOVED}", text)
    text = SECRET_RE.sub(lambda m: f"{m.group(1)}{REMOVED}", text)
    return LONG_RUN_RE.sub(
        lambda m: REMOVED if _looks_like_token(m.group(0)) else m.group(0), text
    )


def keep_plugin(plugin_id):
    """Patterns for a plugin's own ID and the paths of its files.

    A file inside the plugin's folder is named by the plugin's author, not by
    the reporter, so its path after the home folder is kept as it is.
    """
    plugin = re.escape(plugin_id)
    return [
        rf"\.config/omarchy/plugins/{plugin}(?:/[A-Za-z0-9._@+-]+)*",
        plugin,
    ]


class Cleaner:
    """Cleans text for one machine.

    homes are the home path and any other spelling of it, users the
    usernames and hosts the hostnames. Empty values are ignored. keep holds
    regular expressions for text that is never changed, such as keep_plugin's.
    """

    def __init__(self, homes=(), users=(), hosts=(), keep=()):
        homes = {h.rstrip("/") for h in homes if h and h.rstrip("/")}
        self.homes = [
            re.compile(rf"{re.escape(h)}(?![A-Za-z0-9._-])")
            for h in sorted(homes, key=len, reverse=True)
        ]

        def longest_first(values):
            return sorted({v for v in values if v}, key=len, reverse=True)

        self.hosts = [_word(h) for h in longest_first(hosts)]
        self.users = [_word(u) for u in longest_first(users)]
        self.keep = re.compile("(" + "|".join(keep) + ")") if keep else None

    def clean(self, text):
        """Text with personal details removed. Kept text is left as it is."""
        text = strip_colours(text)
        if self.keep is None:
            return self._clean(text)
        # With one group in the pattern, the odd parts are the kept text.
        parts = self.keep.split(text)
        return "".join(
            part if i % 2 else self._clean(part) for i, part in enumerate(parts)
        )

    def _clean(self, text):
        for home in self.homes:
            text = home.sub("~", text)
        text = OTHER_HOME_RE.sub(f"/home/{USER}", text)
        text = EMAIL_RE.sub(EMAIL, text)
        for host in self.hosts:
            text = host.sub(HOST, text)
        for user in self.users:
            text = user.sub(USER, text)
        return _tokens(text)
