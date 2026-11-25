"""The shortcut. The machine is faked: a made-up home in a temporary folder,
fixed output for omarchy and journalctl, and a browser that only records the
link. Git runs for real, on checkouts in the temporary folder, with no user or
system config. Nothing here reads the real home or journal or opens a browser.
"""

import ast
import contextlib
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from omaworks import link, shortcut
from omaworks.shortcut import Stop

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "omaworks")
PLUGIN = "example.sky-clock"
GIT = shutil.which("git")


def git_env(home):
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": home,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Example", "GIT_AUTHOR_EMAIL": "example@example.org",
        "GIT_COMMITTER_NAME": "Example", "GIT_COMMITTER_EMAIL": "example@example.org",
    }


def git(home, folder, *args):
    subprocess.run(
        ["git", "-C", folder, *args], check=True, capture_output=True, env=git_env(home)
    )


def checkout(home, folder, commit=True):
    os.makedirs(folder, exist_ok=True)
    git(home, folder, "init", "-q")
    if commit:
        with open(os.path.join(folder, "manifest.json"), "w") as f:
            f.write("{}\n")
        git(home, folder, "add", ".")
        git(home, folder, "commit", "-q", "-m", "first")


def journal(home, *lines):
    return "\n".join(line.replace("{home}", home) for line in lines) + "\n"


class FakeSystem:
    def __init__(self, home, version=(0, "4.5.0-3\n", ""), log=(0, "", ""),
                 missing=(), opens=True, out=None):
        self._home = home
        self.version = version
        self.log = log
        self.missing = set(missing)
        self.opens = opens
        self.out = out
        self.opened = []
        self.calls = []

    def home(self):
        return self._home

    def users(self):
        return {"mira"}

    def hosts(self):
        return {"mira-laptop.example.lan"}

    def run(self, args):
        self.calls.append(args)
        if args[0] in self.missing:
            raise FileNotFoundError(args[0])
        if args[0] == "omarchy":
            return self.version
        if args[0] == "journalctl":
            return self.log
        if args[0] == "git":
            done = subprocess.run(
                args, capture_output=True, text=True, env=git_env(self._home)
            )
            return done.returncode, done.stdout, done.stderr
        raise AssertionError(f"unexpected command {args}")

    def open(self, url):
        # What was printed by the time the browser opened.
        self.opened.append((url, self.out.getvalue() if self.out else ""))
        return self.opens


def query(url):
    return parse_qs(urlsplit(url).query, keep_blank_values=True)


@unittest.skipUnless(GIT, "needs git")
class ShortcutTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.home = os.path.join(self.tmp, "home", "mira")
        self.plugins = os.path.join(self.home, ".config", "omarchy", "plugins")
        self.folder = os.path.join(self.plugins, PLUGIN)
        os.makedirs(self.plugins)

    def system(self, **kw):
        self.out = io.StringIO()
        return FakeSystem(self.home, out=self.out, **kw)

    def run_report(self, system, plugin=PLUGIN, **kw):
        shortcut.report(plugin, system=system, out=self.out, **kw)
        return self.out.getvalue()

    def assertStops(self, system, words, plugin=PLUGIN, **kw):
        with self.assertRaises(Stop) as stop:
            self.run_report(system, plugin, **kw)
        self.assertIn(words, str(stop.exception))
        self.assertEqual(system.opened, [])
        return str(stop.exception)

    def commit(self):
        done = subprocess.run(
            ["git", "-C", self.folder, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, env=git_env(self.home), check=True,
        )
        return done.stdout.strip()

    # The link

    def test_link_has_the_versions_and_is_opened(self):
        checkout(self.home, self.folder)
        system = self.system()
        printed = self.run_report(system)
        [(url, _)] = system.opened
        self.assertEqual(
            query(url),
            {
                "template": ["report.yml"],
                "title": [f"{PLUGIN} on 4.5.0-3"],
                "plugin": [PLUGIN],
                "omarchy": ["4.5.0-3"],
                "commit": [self.commit()],
            },
        )
        self.assertIn(url, printed)
        self.assertIn("Nothing is sent until you press Submit", printed)

    def test_no_open_prints_the_link_only(self):
        checkout(self.home, self.folder)
        system = self.system()
        printed = self.run_report(system, open_browser=False)
        self.assertEqual(system.opened, [])
        self.assertIn(link.BASE_URL, printed)

    def test_a_symlinked_checkout_is_read(self):
        elsewhere = os.path.join(self.tmp, "src", "sky-clock")
        checkout(self.home, elsewhere)
        os.symlink(elsewhere, self.folder)
        system = self.system()
        self.run_report(system)
        self.assertEqual(query(system.opened[0][0])["commit"], [self.commit()])

    def test_a_release_candidate_is_reported(self):
        checkout(self.home, self.folder)
        system = self.system(version=(0, "4.5.0rc2-1\n", ""))
        self.run_report(system)
        self.assertEqual(query(system.opened[0][0])["omarchy"], ["4.5.0rc2-1"])

    # The plugin

    def test_not_a_plugin_id(self):
        for plugin in ("../evil", "Example.Sky-Clock", "", "a b", ".hidden"):
            with self.subTest(plugin=plugin):
                self.assertStops(self.system(), "isn't a plugin ID", plugin=plugin)

    def test_plugin_not_installed(self):
        message = self.assertStops(self.system(), "isn't installed")
        self.assertIn(f"~/.config/omarchy/plugins/{PLUGIN}", message)
        self.assertNotIn(self.home, message)

    def test_a_file_or_broken_link_is_not_installed(self):
        os.symlink(os.path.join(self.tmp, "gone"), self.folder)
        self.assertStops(self.system(), "isn't installed")
        os.remove(self.folder)
        open(self.folder, "w").close()
        self.assertStops(self.system(), "isn't installed")

    def test_not_a_git_checkout(self):
        os.makedirs(self.folder)
        self.assertStops(self.system(), "isn't a git checkout")

    def test_a_folder_inside_another_checkout_is_not_guessed(self):
        # Such as a dotfiles repo that holds ~/.config.
        checkout(self.home, self.home)
        os.makedirs(self.folder)
        self.assertStops(self.system(), "isn't a git checkout")

    def test_a_link_into_part_of_a_checkout_is_not_guessed(self):
        repo = os.path.join(self.tmp, "src", "suite")
        checkout(self.home, repo)
        os.makedirs(os.path.join(repo, "clock"))
        os.symlink(os.path.join(repo, "clock"), self.folder)
        self.assertStops(self.system(), "isn't a git checkout")

    def test_a_checkout_with_no_commit(self):
        checkout(self.home, self.folder, commit=False)
        self.assertStops(self.system(), "has no commit yet")

    def test_git_missing(self):
        checkout(self.home, self.folder)
        self.assertStops(self.system(missing={"git"}), "Can't find git")

    def test_git_printing_something_odd(self):
        os.makedirs(self.folder)
        system = self.system()
        answers = iter([(0, self.folder + "\n", ""), (0, "not-a-commit\n", "")])
        system.run = lambda args: (0, "4.5.0-3\n", "") if args[0] == "omarchy" else next(answers)
        self.assertStops(system, "isn't a commit")

    # The Omarchy version

    def test_omarchy_missing(self):
        checkout(self.home, self.folder)
        self.assertStops(self.system(missing={"omarchy"}), "Can't find the omarchy command")

    def test_omarchy_version_fails(self):
        checkout(self.home, self.folder)
        self.assertStops(self.system(version=(1, "", "")), "`omarchy version` failed")

    def test_omarchy_version_prints_nothing(self):
        checkout(self.home, self.folder)
        self.assertStops(self.system(version=(0, " \n", "")), "printed nothing")

    def test_a_development_build(self):
        checkout(self.home, self.folder)
        for version in ("dev (3ac4365)", "dev", "4.0.0.r7195.g3ac4365-1"):
            with self.subTest(version=version):
                self.assertStops(
                    self.system(version=(0, version + "\n", "")), "development build"
                )

    def test_not_a_version(self):
        checkout(self.home, self.folder)
        self.assertStops(
            self.system(version=(0, "\x1b[31mnope\x1b[0m\n", "")),
            "isn't a version: nope",
        )

    def test_more_than_a_version(self):
        checkout(self.home, self.folder)
        self.assertStops(
            self.system(version=(0, "4.5.0-3\nextra\n", "")), "more than a version"
        )

    # --logs

    LOG = (
        "\x1b[33m  WARN\x1b[97m scene\x1b[0m: qs://{home}/.config/omarchy/plugins/example.sky-clock/Panel.qml:41:5: TypeError: Cannot read property 'hour' of null",
        "\x1b[33m  WARN\x1b[97m quickshell.qmlscanner\x1b[0m: Module path \"{home}/.config/omarchy/plugins/example.sky-clock/widgets\" is outside of the config folder.",
        "\x1b[33m  WARN\x1b[0m: qs://{home}/.config/omarchy/plugins/example.sky-clock-pro/Bar.qml:3:1: not ours",
        "\x1b[33m  WARN\x1b[0m: qs:///usr/share/omarchy/shell/plugins/clock/Clock.qml:9:1: built in",
        "  INFO: mira-laptop started for mira",
        "\x1b[33m  WARN\x1b[97m scene\x1b[0m: qs://{home}/.config/omarchy/plugins/example.sky-clock/Panel.qml:41:5: TypeError: Cannot read property 'hour' of null",
        "\x1b[33m  WARN\x1b[0m: file://{home}/.config/omarchy/plugins/example.sky-clock/sync.js[7:-1]: fetch for mira on mira-laptop failed, token=abc123secret",
    )

    def test_logs_are_picked_cleaned_and_shown_before_the_form(self):
        checkout(self.home, self.folder)
        system = self.system(log=(0, journal(self.home, *self.LOG), ""))
        self.run_report(system, logs=True)
        [(url, printed_before)] = system.opened
        expected = [
            "WARN scene: qs://~/.config/omarchy/plugins/example.sky-clock/Panel.qml:41:5: "
            "TypeError: Cannot read property 'hour' of null",
            "WARN: file://~/.config/omarchy/plugins/example.sky-clock/sync.js[7:-1]: "
            "fetch for <user> on <host> failed, token=<removed>",
        ]
        self.assertEqual(query(url)["errors"], ["\n".join(expected)])
        for line in expected:
            self.assertIn(f"  {line}\n", printed_before)
        for text in ("mira", "abc123secret", "\x1b", "not ours", "built in", "outside"):
            self.assertNotIn(text, printed_before.replace("example.sky-clock", ""))
            self.assertNotIn(text, query(url)["errors"][0])
        self.assertIn(shortcut.JOURNAL, system.calls)

    def test_the_journal_command_reads_the_shell_since_boot(self):
        self.assertEqual(shortcut.JOURNAL[:2], ["journalctl", "--user"])
        for flag in ("--boot", "--quiet", "--no-pager"):
            self.assertIn(flag, shortcut.JOURNAL)
        self.assertEqual(
            shortcut.JOURNAL[shortcut.JOURNAL.index("--identifier") + 1], "omarchy-shell"
        )

    def test_no_lines_in_the_log(self):
        checkout(self.home, self.folder)
        system = self.system(log=(0, journal(self.home, *self.LOG[2:5]), ""))
        printed = self.run_report(system, logs=True)
        self.assertIn("has no lines from example.sky-clock", printed)
        self.assertNotIn("errors", query(system.opened[0][0]))

    def test_without_logs_the_journal_is_not_read(self):
        checkout(self.home, self.folder)
        system = self.system(log=(0, journal(self.home, *self.LOG), ""))
        self.run_report(system)
        self.assertNotIn(shortcut.JOURNAL, system.calls)
        self.assertNotIn("errors", query(system.opened[0][0]))

    def test_journalctl_missing(self):
        checkout(self.home, self.folder)
        self.assertStops(self.system(missing={"journalctl"}), "Can't find journalctl", logs=True)

    def test_journalctl_fails(self):
        checkout(self.home, self.folder)
        self.assertStops(self.system(log=(1, "", "")), "couldn't read the shell's log", logs=True)

    def test_too_many_lines_are_left_out_of_the_link(self):
        checkout(self.home, self.folder)
        lines = [
            f"WARN: qs://{{home}}/.config/omarchy/plugins/example.sky-clock/Panel.qml:{n}:1: x"
            for n in range(200)
        ]
        system = self.system(log=(0, journal(self.home, *lines), ""))
        printed = self.run_report(system, logs=True)
        [(url, before)] = system.opened
        self.assertNotIn("errors", query(url))
        self.assertLessEqual(len(url), link.MAX_LINK_LENGTH)
        self.assertIn("Paste them into the form's Error lines yourself", before)
        self.assertIn("Panel.qml:199:1: x", printed)

    # The browser

    def test_browser_failing_says_so_after_printing_the_link(self):
        checkout(self.home, self.folder)
        system = self.system(opens=False)
        with self.assertRaises(Stop) as stop:
            self.run_report(system)
        self.assertIn("Open the link above yourself", str(stop.exception))
        self.assertIn(system.opened[0][0], self.out.getvalue())

    # Nothing leaves the machine

    def test_no_network_is_used(self):
        checkout(self.home, self.folder)
        system = self.system(log=(0, journal(self.home, *self.LOG), ""))
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network")), \
                mock.patch.object(socket, "getaddrinfo", side_effect=AssertionError("network")):
            self.run_report(system, logs=True)
        self.assertEqual(len(system.opened), 1)

    def test_main_prints_a_plain_message_and_exits_1(self):
        out, err = io.StringIO(), io.StringIO()
        code = shortcut.main(["report", PLUGIN], system=self.system(), out=out, err=err)
        self.assertEqual(code, 1)
        self.assertTrue(err.getvalue().startswith("omaworks: example.sky-clock isn't installed"))
        self.assertNotIn("Traceback", err.getvalue())

    def test_main_succeeds(self):
        checkout(self.home, self.folder)
        system = self.system()
        code = shortcut.main(["report", "--no-open", PLUGIN], system=system, out=self.out)
        self.assertEqual(code, 0)
        self.assertEqual(system.opened, [])

    def test_usage_errors(self):
        for argv in ([], ["report"], ["report", "--agent", PLUGIN], ["send", PLUGIN]):
            with self.subTest(argv=argv):
                err = io.StringIO()
                with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as exit:
                    shortcut.main(argv, system=self.system())
                self.assertEqual(exit.exception.code, 2)
                self.assertIn("usage: omaworks", err.getvalue())


class SystemTest(unittest.TestCase):
    def test_git_variables_are_not_passed_on(self):
        with mock.patch.dict(os.environ, {"GIT_DIR": "/elsewhere", "GIT_WORK_TREE": "/x"}):
            env = shortcut.System.env()
        self.assertNotIn("GIT_DIR", env)
        self.assertNotIn("GIT_WORK_TREE", env)
        self.assertIn("PATH", env)

    def test_no_network_or_github_code_is_imported(self):
        for name in ("shortcut.py", "clean.py"):
            with open(os.path.join(ROOT, "omaworks", name)) as f:
                tree = ast.parse(f.read())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported |= {a.name for a in node.names}
                elif isinstance(node, ast.ImportFrom):
                    imported.add(node.module)
            with self.subTest(name=name):
                for banned in ("urllib.request", "http.client", "omaworks.github", "ssl"):
                    self.assertNotIn(banned, imported)
            with open(os.path.join(ROOT, "omaworks", name)) as f:
                source = f.read()
            for token in ("GITHUB_TOKEN", "GH_TOKEN", "gh auth"):
                self.assertNotIn(token, source)


@unittest.skipUnless(GIT, "needs git")
class CommandTest(unittest.TestCase):
    """bin/omaworks itself, with omarchy, journalctl and xdg-open faked on PATH."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.home = os.path.join(self.tmp, "home", "mira")
        self.fakebin = os.path.join(self.tmp, "bin")
        self.opened = os.path.join(self.tmp, "opened")
        os.makedirs(self.fakebin)
        for name, body in {
            "omarchy": 'echo 4.5.0-3',
            "journalctl": "exit 0",
            "xdg-open": f'printf "%s" "$1" > "{self.opened}"',
        }.items():
            path = os.path.join(self.fakebin, name)
            with open(path, "w") as f:
                f.write(f"#!/bin/sh\n{body}\n")
            os.chmod(path, 0o755)

    def run_bin(self, *args):
        # The fakes come first, so the real omarchy, journalctl and xdg-open
        # are never run.
        env = git_env(self.home)
        env["PATH"] = os.pathsep.join([self.fakebin, os.path.dirname(GIT)])
        env["USER"] = "mira"
        return subprocess.run(
            [sys.executable, BIN, *args], capture_output=True, text=True, env=env,
            timeout=60,
        )

    def test_help(self):
        done = self.run_bin("report", "--help")
        self.assertEqual(done.returncode, 0)
        self.assertIn("--logs", done.stdout)

    def test_report_opens_the_form(self):
        folder = os.path.join(self.home, ".config", "omarchy", "plugins", PLUGIN)
        checkout(self.home, folder)
        done = self.run_bin("report", "--logs", PLUGIN)
        self.assertEqual(done.returncode, 0, done.stderr)
        with open(self.opened) as f:
            url = f.read()
        self.assertIn(url, done.stdout)
        self.assertEqual(query(url)["omarchy"], ["4.5.0-3"])

    def test_not_installed(self):
        done = self.run_bin("report", PLUGIN)
        self.assertEqual(done.returncode, 1)
        self.assertIn("isn't installed", done.stderr)
        self.assertFalse(os.path.exists(self.opened))


if __name__ == "__main__":
    unittest.main()
