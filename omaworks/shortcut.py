"""The shortcut: `omaworks report <plugin>`.

See SPEC.md, "The shortcut". It reads the Omarchy version and the plugin's
commit on this machine, builds the link to the report form, prints it and
opens it in the browser. With --logs it adds the plugin's lines from the
shell's log, cleaned of personal details and shown first. --what-file and
--errors-file take a draft's text from files, cleaned the same way. Files,
because the text is untrusted and must never be quoted into a shell
command. --agent hands the
report to the default coding agent instead: see omaworks/agent.py.

It sends nothing and needs no GitHub token. The reporter presses Submit.
Anything it can't find stops it with a plain message. Nothing is guessed.

The machine is reached only through a System, so tests hand in a fake one.
"""

import argparse
import os
import pwd
import re
import shutil
import socket
import subprocess
import sys

from omaworks import agent as agent_option
from omaworks.check import COMMIT_RE, DEV_RE, ID_RE, release_of
from omaworks.clean import Cleaner, keep_plugin, strip_colours
from omaworks.link import LinkTooLong, build_report_link

PLUGINS = os.path.join(".config", "omarchy", "plugins")

JOURNAL = [
    "journalctl", "--user", "--identifier", "omarchy-shell", "--boot",
    "--output", "cat", "--no-pager", "--quiet",
]

# The shell says this once for every plugin in ~/.config/omarchy/plugins.
# It is about where plugins live, not about the plugin.
NOISE = [
    re.compile(r'Module path ".*" is outside of the config folder\.'),
]

# Longest output of a command quoted back in a message.
MAX_QUOTE = 80

TIMEOUT = 30

# Largest draft file read for --what-file or --errors-file. The link holds
# far less, so anything bigger is not a draft.
MAX_DRAFT = 64 * 1024


class Stop(Exception):
    """The shortcut can't go on. The message says why, in plain words."""


class System:
    """This machine: its home, names and commands."""

    def home(self):
        return os.path.expanduser("~")

    def users(self):
        names = {os.environ.get("USER", ""), os.environ.get("LOGNAME", "")}
        try:
            names.add(pwd.getpwuid(os.getuid()).pw_name)
        except KeyError:
            pass
        return names

    def hosts(self):
        # gethostname only asks the kernel. getfqdn could ask the network.
        return {socket.gethostname()}

    @staticmethod
    def env():
        # GIT_DIR and its friends would point git at another checkout.
        return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def run(self, args):
        """(exit code, output, errors). Raises OSError when there's no such
        command."""
        try:
            done = subprocess.run(
                args, capture_output=True, text=True, errors="replace",
                stdin=subprocess.DEVNULL, env=self.env(), timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return 124, "", f"took longer than {TIMEOUT} seconds"
        return done.returncode, done.stdout, done.stderr

    @staticmethod
    def terminal():
        """True when this runs in a terminal, for both input and output."""
        return sys.stdin.isatty() and sys.stdout.isatty()

    @staticmethod
    def has(command):
        """True when command is on PATH."""
        return shutil.which(command) is not None

    @staticmethod
    def start_agent(args):
        """Replace this process with args. Raises OSError when it can't, before
        anything is replaced."""
        sys.stdout.flush()
        sys.stderr.flush()
        os.execvp(args[0], args)

    def open(self, url):
        """Open url with xdg-open. False when it says it failed."""
        try:
            child = subprocess.Popen(
                ["xdg-open", url], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return False
        try:
            return child.wait(timeout=10) == 0
        except subprocess.TimeoutExpired:
            # Some browsers keep xdg-open waiting while they run.
            return True


def _quote(text):
    """The first line of text, short and without colour codes."""
    lines = strip_colours(text).strip().splitlines()
    text = lines[0] if lines else ""
    return text if len(text) <= MAX_QUOTE else text[: MAX_QUOTE - 1] + "…"


def omarchy_version(system):
    """What `omarchy version` prints, when it is a release version."""
    try:
        code, out, _ = system.run(["omarchy", "version"])
    except OSError:
        raise Stop(
            "Can't find the omarchy command, so the Omarchy version is unknown."
        ) from None
    if code != 0:
        raise Stop("`omarchy version` failed, so the Omarchy version is unknown.")
    version = out.strip()
    if not version:
        raise Stop("`omarchy version` printed nothing, so the Omarchy version is unknown.")
    if "\n" in version or len(version) > MAX_QUOTE:
        raise Stop(
            f"`omarchy version` printed more than a version: {_quote(version)}"
        )
    if DEV_RE.fullmatch(version.lower()):
        raise Stop(
            f"This is a development build of Omarchy ({version}). Reports are "
            "counted per release, so report on a release or a release candidate."
        )
    if release_of(version) is None:
        raise Stop(
            f"`omarchy version` printed something that isn't a version: {_quote(version)}"
        )
    return version


def plugin_folder(system, plugin):
    """The plugin's folder in ~/.config/omarchy/plugins."""
    if not ID_RE.fullmatch(plugin):
        raise Stop(
            f"{_quote(plugin)!r} isn't a plugin ID. Use the ID of an installed "
            "plugin, in lowercase, such as example.sky-clock."
        )
    folder = os.path.join(system.home(), PLUGINS, plugin)
    if not os.path.isdir(folder):
        raise Stop(
            f"{plugin} isn't installed: there is no folder "
            f"~/{PLUGINS}/{plugin}. `omarchy plugin list` shows what is."
        )
    return folder


def plugin_commit(system, plugin, folder):
    """The short commit of the plugin's own git checkout."""
    def git(*args):
        try:
            return system.run(["git", "-C", folder, *args])
        except OSError:
            raise Stop("Can't find git, so the plugin's commit is unknown.") from None

    not_git = (
        f"~/{PLUGINS}/{plugin} isn't a git checkout, so the plugin's commit is "
        "unknown. Plugins added with `omarchy plugin add` are."
    )
    code, out, _ = git("rev-parse", "--show-toplevel")
    if code != 0 or not out.strip():
        raise Stop(not_git)
    # A folder inside some other checkout, such as a dotfiles repo in ~/.config,
    # would give that checkout's commit.
    if os.path.realpath(out.strip()) != os.path.realpath(folder):
        raise Stop(not_git)
    code, out, _ = git("rev-parse", "--short", "HEAD")
    commit = out.strip()
    if code != 0 or not commit:
        raise Stop(
            f"~/{PLUGINS}/{plugin} has no commit yet, so there is nothing to report on."
        )
    if not COMMIT_RE.fullmatch(commit):
        raise Stop(f"git printed something that isn't a commit: {_quote(commit)}")
    return commit


def cleaner(system, plugin):
    home = system.home()
    homes = {home, os.path.realpath(home)}
    users = set(system.users()) | {os.path.basename(h.rstrip("/")) for h in homes}
    hosts = set()
    for host in system.hosts():
        hosts |= {host, host.split(".")[0]}
    return Cleaner(homes=homes, users=users, hosts=hosts, keep=keep_plugin(plugin))


def log_lines(system, plugin):
    """The plugin's lines from the shell's log since the last boot, cleaned.

    A line is the plugin's when it names a file in the plugin's folder.
    Repeated lines are shown once.
    """
    try:
        code, out, _ = system.run(JOURNAL)
    except OSError:
        raise Stop("Can't find journalctl, so --logs can't read the shell's log.") from None
    if code != 0:
        raise Stop("journalctl couldn't read the shell's log, so --logs has nothing to add.")
    home = system.home()
    folders = {
        os.path.join(h, PLUGINS, plugin) + "/"
        for h in (home, os.path.realpath(home))
    }
    clean = cleaner(system, plugin)
    lines, seen = [], set()
    for raw in out.splitlines():
        line = strip_colours(raw).rstrip()
        if not any(folder in line for folder in folders):
            continue
        if any(noise.search(line) for noise in NOISE):
            continue
        line = clean.clean(line).strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return lines


def read_draft(path, option):
    """The text of a draft file, as UTF-8. Raises Stop."""
    name = _quote(path)
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_DRAFT + 1)
    except FileNotFoundError:
        raise Stop(f"{option}: there is no file {name}.") from None
    except IsADirectoryError:
        raise Stop(f"{option}: {name} is a folder, not a file.") from None
    except OSError as e:
        raise Stop(f"{option}: can't read {name}: {e.strerror or e}.") from None
    if len(data) > MAX_DRAFT:
        raise Stop(
            f"{option}: {name} is bigger than {MAX_DRAFT // 1024} KB, too big for a draft."
        )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise Stop(f"{option}: {name} isn't UTF-8 text.") from None


def _draft(clean, text):
    """The reporter's or the agent's text, cleaned line by line."""
    if not text:
        return None
    lines = [clean.clean(line).rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines).strip() or None


def _show(out, heading, text):
    print(heading, file=out)
    print("", file=out)
    for line in text.splitlines():
        print(f"  {line}", file=out)
    print("", file=out)


def report(plugin, logs=False, open_browser=True, system=None, out=None,
           what=None, errors=None):
    """Build the link, print it and open it. Raises Stop.

    what and errors are a draft's What happens and Error lines, as read by
    read_draft. They are cleaned of personal details before they go into the
    link.
    """
    system = system or System()
    out = out or sys.stdout
    folder = plugin_folder(system, plugin)
    version = omarchy_version(system)
    commit = plugin_commit(system, plugin, folder)

    clean = cleaner(system, plugin)
    what = _draft(clean, what)
    errors = _draft(clean, errors)
    if logs:
        lines = log_lines(system, plugin)
        if lines:
            errors = "\n".join(lines)
            _show(
                out,
                "The plugin's lines from the shell's log, with personal details removed:",
                errors,
            )
        else:
            print(f"The shell's log has no lines from {plugin} since the last boot.", file=out)

    def build():
        try:
            return build_report_link(plugin, version, commit, what=what, errors=errors)
        except LinkTooLong:
            return None

    # Too long: the error lines go first, then What happens. Each is shown
    # here for the reporter to paste.
    link = build()
    if link is None and errors is not None:
        if not logs:
            _show(out, "Error lines, with personal details removed:", errors)
        errors = None
        print(
            "These lines make the link too long, so they are left out. Paste them "
            "into the form's Error lines yourself.",
            file=out,
        )
        link = build()
    if link is None and what is not None:
        _show(out, "What happens, with personal details removed:", what)
        what = None
        print(
            "This text makes the link too long, so it is left out. Paste it "
            "into the form's What happens yourself.",
            file=out,
        )
        link = build()
    if link is None:
        raise Stop("The link to the form is too long to open.")

    print(f"Omarchy {version}, {plugin} at {commit}.", file=out)
    if not open_browser:
        print(link, file=out)
        return
    print("Opening the report form. Nothing is sent until you press Submit:", file=out)
    print(link, file=out)
    if not system.open(link):
        raise Stop("xdg-open couldn't open the browser. Open the link above yourself.")


def agent(plugin, system=None, out=None):
    """Start the default coding agent on the report. Raises Stop.

    The plugin is checked first, so a typo doesn't start the agent. The
    agent reads the versions itself, through `omaworks report`.

    The agent starts in the current folder, never in the plugin's checkout:
    a checkout can hold an AGENTS.md or CLAUDE.md by the plugin's author,
    which many agents would load as instructions.
    """
    system = system or System()
    out = out or sys.stdout
    plugin_folder(system, plugin)
    if not system.has(agent_option.PROMPT_COMMAND):
        raise Stop(
            f"Can't find {agent_option.PROMPT_COMMAND}, so --agent can't start "
            "your agent. It comes with Omarchy."
        )
    args = agent_option.command_line(plugin, inline=system.terminal())
    print(
        f"Starting your default coding agent on {plugin}. It stops at the "
        "filled-in form. Nothing is sent until you press Submit.",
        file=out,
    )
    try:
        system.start_agent(args)
    except OSError:
        raise Stop(
            f"Can't run {agent_option.PROMPT_COMMAND}, so --agent can't start your agent."
        ) from None


def parser():
    top = argparse.ArgumentParser(
        prog="omaworks",
        description="Report whether an Omarchy plugin works on your Omarchy version.",
    )
    commands = top.add_subparsers(dest="command", required=True, metavar="command")
    cmd = commands.add_parser(
        "report",
        # --what would otherwise be taken for --what-file, and the text for a path.
        allow_abbrev=False,
        help="open the report form with this machine's versions filled in",
        description=(
            "Open the report form with the Omarchy version and the plugin's "
            "commit filled in. Nothing is sent until you press Submit."
        ),
    )
    cmd.add_argument("plugin", help="the plugin's ID, such as example.sky-clock")
    cmd.add_argument(
        "--logs", action="store_true",
        help="add the plugin's lines from the shell's log since the last boot, "
        "with personal details removed",
    )
    cmd.add_argument(
        "--what-file", metavar="PATH",
        help="fill in What happens with the text in this file, with personal "
        "details removed",
    )
    cmd.add_argument(
        "--errors-file", metavar="PATH",
        help="fill in Error lines with the lines in this file, with personal "
        "details removed",
    )
    cmd.add_argument(
        "--no-open", dest="open", action="store_false",
        help="print the link without opening the browser",
    )
    cmd.add_argument(
        "--agent", action="store_true",
        help="let your default coding agent look into it and fill in the form. "
        "It stops at the form, and you press Submit",
    )
    return top


def main(argv=None, system=None, out=None, err=None):
    out = out or sys.stdout
    err = err or sys.stderr
    top = parser()
    args = top.parse_args(argv)
    if args.agent:
        given = [
            flag for flag, used in (
                ("--logs", args.logs), ("--what-file", args.what_file is not None),
                ("--errors-file", args.errors_file is not None),
                ("--no-open", not args.open),
            ) if used
        ]
        if given:
            top.error(f"--agent can't be used with {', '.join(given)}: the agent fills in the form")
    if args.logs and args.errors_file is not None:
        top.error("--logs and --errors-file both fill in Error lines: use one")
    try:
        if args.agent:
            agent(args.plugin, system=system, out=out)
        else:
            what = errors = None
            if args.what_file is not None:
                what = read_draft(args.what_file, "--what-file")
            if args.errors_file is not None:
                errors = read_draft(args.errors_file, "--errors-file")
            report(
                args.plugin, logs=args.logs, open_browser=args.open, system=system,
                out=out, what=what, errors=errors,
            )
    except Stop as stop:
        print(f"omaworks: {stop}", file=err)
        return 1
    return 0
