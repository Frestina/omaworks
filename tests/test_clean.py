"""Cleaning log lines. Every name, path and token here is made up."""

import unittest

from omaworks.clean import Cleaner, keep_plugin, strip_colours

HOME = "/home/mira"


def cleaner(**kw):
    kw.setdefault("homes", [HOME])
    kw.setdefault("users", ["mira"])
    kw.setdefault("hosts", ["mira-laptop"])
    return Cleaner(**kw)


class ColourTest(unittest.TestCase):
    def test_colour_codes_are_stripped(self):
        line = "\x1b[33m  WARN\x1b[97m scene\x1b[0m: TypeError"
        self.assertEqual(strip_colours(line), "  WARN scene: TypeError")

    def test_other_escapes_and_control_characters_are_stripped(self):
        line = "\x1b]8;;https://example.org\x1b\\link\x1b]8;;\x1b\\ a\x07b\x1bc\tend"
        self.assertEqual(strip_colours(line), "link abc\tend")

    def test_cleaning_strips_colours(self):
        self.assertEqual(cleaner().clean("\x1b[31mBroken\x1b[0m"), "Broken")


class HomeTest(unittest.TestCase):
    def test_home_path_becomes_tilde(self):
        line = "qs:///home/mira/.config/omarchy/plugins/example.sky-clock/Panel.qml:41:5: x"
        self.assertEqual(
            cleaner().clean(line),
            "qs://~/.config/omarchy/plugins/example.sky-clock/Panel.qml:41:5: x",
        )

    def test_home_itself_and_with_a_colon(self):
        self.assertEqual(cleaner().clean("cd /home/mira; /home/mira:12"), "cd ~; ~:12")

    def test_another_spelling_of_home(self):
        c = cleaner(homes=[HOME, "/var/home/mira/"])
        self.assertEqual(c.clean("file:///var/home/mira/notes.txt"), "file://~/notes.txt")

    def test_a_longer_name_is_not_the_home(self):
        self.assertEqual(cleaner().clean("/home/miranda/x"), "/home/<user>/x")

    def test_any_other_home_is_removed(self):
        self.assertEqual(
            cleaner().clean("read /home/olek.b/.cache/x and /home/guest"),
            "read /home/<user>/.cache/x and /home/<user>",
        )


class NameTest(unittest.TestCase):
    def test_hostname_is_removed(self):
        self.assertEqual(
            cleaner().clean("connected to mira-laptop on port 5"),
            "connected to <host> on port 5",
        )

    def test_hostname_holding_the_username_goes_whole(self):
        self.assertEqual(cleaner().clean("MIRA-LAPTOP says hi"), "<host> says hi")

    def test_username_is_removed_as_a_word(self):
        self.assertEqual(
            cleaner().clean("owner mira, Mira's file, mira_old"),
            "owner <user>, <user>'s file, <user>_old",
        )

    def test_username_inside_a_longer_word_stays(self):
        self.assertEqual(cleaner().clean("a mirage of admiral"), "a mirage of admiral")

    def test_empty_names_are_ignored(self):
        c = Cleaner(homes=["", "/"], users=[""], hosts=[""])
        self.assertEqual(c.clean("plain text"), "plain text")

    def test_email_is_removed(self):
        self.assertEqual(
            cleaner().clean("mail mira.k+omarchy@example.org now"),
            "mail <email> now",
        )


class TokenTest(unittest.TestCase):
    def assertRemoved(self, secret, line=None):
        line = line or f"value {secret} end"
        cleaned = cleaner().clean(line)
        self.assertNotIn(secret, cleaned)
        self.assertIn("<removed>", cleaned)
        return cleaned

    def test_tokens_with_a_known_prefix(self):
        # Each value is joined here from a prefix and a body, so no whole
        # token is one literal in the source. Secret scanners such as GitHub's
        # push protection would take a whole one for a real secret.
        for prefix, body in (
            ("gh" + "p_", "Ab12Cd34Ef56Gh78Ij90Kl12"),
            ("github" + "_pat_", "11ABCDEFG0abcdefghij_klmnop"),
            ("gl" + "pat-", "abcdEFGH1234ijklMNOP"),
            ("xo" + "xb-", "1234567890-abcdefghij"),
            ("AK" + "IA", "ABCDEFGHIJKLMNOP"),
            ("sk" + "-ant-", "abcdefgh12345678"),
        ):
            secret = prefix + body
            with self.subTest(prefix=prefix):
                self.assertRemoved(secret)

    def test_named_secrets(self):
        cases = {
            "pw": "password=hunter2",
            "key": '"api_key": "kitten7"',
            "token": "TOKEN: abc",
            "cookie": "cookie=sess1",
        }
        for name, line in cases.items():
            with self.subTest(name=name):
                cleaned = cleaner().clean(line)
                for secret in ("hunter2", "kitten7", "abc", "sess1"):
                    self.assertNotIn(secret, cleaned)
                self.assertIn("<removed>", cleaned)

    def test_bearer_header(self):
        self.assertEqual(
            cleaner().clean("Authorization: Bearer abc.DEF-123_xyz"),
            "Authorization: Bearer <removed>",
        )
        self.assertEqual(
            cleaner().clean("sent Bearer abc.DEF-123_xyz"), "sent Bearer <removed>"
        )

    def test_long_hex(self):
        self.assertRemoved("c0ffee00" * 4)

    def test_long_mixed_run(self):
        self.assertRemoved("aGVsbG8gd29y" + "bGQgdGhpcyBp" + "cyBhIHRlc3Q=")
        self.assertRemoved("Zm9vYmFy/YmF6" + "cXV4+cXV1eA1" + "234567890ab")


class LeftAloneTest(unittest.TestCase):
    def test_a_usual_qml_warning_keeps_its_details(self):
        line = (
            "WARN scene: TypeError: Property 'shellQuote' of object "
            "PluginBarApi_QMLTYPE_26(0x7f00deadbeef) is not a function"
        )
        self.assertEqual(cleaner().clean(line), line)

    def test_system_paths_and_long_words_stay(self):
        line = (
            "qs:///usr/share/omarchy/shell/plugins/lock/Service.qml:503:17 "
            "/usr/lib/qt6/qml/QtQuick/Controls/Basic/implVeryLongName2 "
            "an_ordinary_but_quite_long_identifier_name"
        )
        self.assertEqual(cleaner().clean(line), line)


class KeepTest(unittest.TestCase):
    def test_plugin_id_holding_the_username_is_kept(self):
        # omarchy plugin clone names a clone <username>.<id>.
        c = cleaner(keep=keep_plugin("mira.sky-clock"))
        line = "Plugin widget mira.sky-clock failed: file:///home/mira/.config/omarchy/plugins/mira.sky-clock/Panel.qml: mira"
        self.assertEqual(
            c.clean(line),
            "Plugin widget mira.sky-clock failed: "
            "file://~/.config/omarchy/plugins/mira.sky-clock/Panel.qml: <user>",
        )

    def test_files_inside_the_plugin_keep_their_paths(self):
        c = cleaner(keep=keep_plugin("example.sky-clock"))
        path = ".config/omarchy/plugins/example.sky-clock/widgets/ClockFace2Component1234567/Main.qml"
        self.assertEqual(c.clean(f"/home/mira/{path}:3"), f"~/{path}:3")

    def test_kept_text_is_literal(self):
        c = cleaner(keep=keep_plugin("example.sky-clock"))
        self.assertEqual(c.clean("exampleXsky-clock mira"), "exampleXsky-clock <user>")


if __name__ == "__main__":
    unittest.main()
