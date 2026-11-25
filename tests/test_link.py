import unittest
from urllib.parse import parse_qs, urlsplit

from omaworks import link
from omaworks.link import LinkError, LinkTooLong, build_form_link, build_report_link

REQUIRED = dict(plugin="example.sky-clock", omarchy="4.5.0-3", commit="3f2a91c")


def query(url):
    return parse_qs(urlsplit(url).query, keep_blank_values=True)


class BuildReportLinkTest(unittest.TestCase):
    def test_basic_link(self):
        url = build_report_link(**REQUIRED)
        self.assertTrue(url.startswith("https://github.com/Frestina/omaworks/issues/new?"))
        self.assertEqual(
            query(url),
            {
                "template": ["report.yml"],
                "title": ["example.sky-clock on 4.5.0-3"],
                "plugin": ["example.sky-clock"],
                "omarchy": ["4.5.0-3"],
                "commit": ["3f2a91c"],
            },
        )

    # Plugins that aren't in the marketplace are named by their repo URL, and
    # the values come from other programs, so every character is encoded.

    def test_spaces_are_percent_20_not_plus(self):
        url = build_report_link(**REQUIRED | dict(omarchy="4.5 beta"))
        self.assertIn("omarchy=4.5%20beta", url)
        self.assertNotIn("+", url)

    def test_ampersand_does_not_split_a_value(self):
        url = build_report_link("a&b=c")
        self.assertIn("plugin=a%26b%3Dc", url)
        self.assertEqual(query(url)["plugin"], ["a&b=c"])

    def test_hash_does_not_start_a_fragment(self):
        url = build_report_link("https://github.com/example-dev/clock#12")
        self.assertNotIn("#", url)
        self.assertEqual(query(url)["plugin"], ["https://github.com/example-dev/clock#12"])

    def test_newlines_are_encoded(self):
        url = build_report_link("one\ntwo")
        self.assertIn("plugin=one%0Atwo", url)
        self.assertNotIn("\n", url)

    def test_non_ascii_is_utf8_percent_encoded(self):
        url = build_report_link("café")
        self.assertIn("plugin=caf%C3%A9", url)
        self.assertTrue(url.isascii())

    def test_optional_fields_left_out_when_missing_or_empty(self):
        url = build_report_link("example.sky-clock", "", "  ")
        self.assertEqual(set(query(url)), {"template", "title", "plugin"})

    def test_free_text_cannot_go_in_the_link(self):
        # GitHub locks every field a link fills in. See SPEC.md, "Only the
        # fixed fields go in the link".
        for field in ("what", "errors"):
            with self.subTest(field=field):
                with self.assertRaises(TypeError):
                    build_report_link(**REQUIRED, **{field: "The clock is gone."})
        self.assertEqual(
            set(query(build_report_link(**REQUIRED))),
            {"template", "title", "plugin", "omarchy", "commit"},
        )

    def test_no_result_in_link(self):
        self.assertNotIn("result", query(build_report_link(**REQUIRED)))
        with self.assertRaises(TypeError):
            build_report_link(**REQUIRED, result="Works")

    def test_title_with_version(self):
        self.assertEqual(
            query(build_report_link(**REQUIRED))["title"],
            ["example.sky-clock on 4.5.0-3"],
        )

    def test_title_without_version(self):
        self.assertEqual(
            query(build_report_link("example.sky-clock"))["title"],
            ["example.sky-clock"],
        )

    def test_plugin_only_link(self):
        q = query(build_report_link("example.sky-clock"))
        self.assertEqual(set(q), {"template", "title", "plugin"})

    def test_plugin_required(self):
        for value in ("", "  ", None):
            with self.subTest(value=value):
                with self.assertRaises(LinkError):
                    build_report_link(value, "4.5.0-3", "3f2a91c")

    def test_values_stripped(self):
        url = build_report_link(" example.sky-clock ", "4.5.0-3\n", "\n3f2a91c\n")
        q = query(url)
        self.assertEqual(q["plugin"], ["example.sky-clock"])
        self.assertEqual(q["omarchy"], ["4.5.0-3"])
        self.assertEqual(q["commit"], ["3f2a91c"])
        self.assertEqual(q["title"], ["example.sky-clock on 4.5.0-3"])
        self.assertNotIn("%0A", url)

    def test_too_long_link_refused(self):
        with self.assertRaises(LinkTooLong):
            build_report_link(**REQUIRED | dict(commit="x" * link.MAX_LINK_LENGTH))

    def test_length_counts_the_encoded_link(self):
        # Short as text, long once every é becomes %C3%A9.
        with self.assertRaises(LinkTooLong):
            build_report_link(**REQUIRED | dict(commit="é" * (link.MAX_LINK_LENGTH // 5)))

    def test_link_just_under_the_limit_is_accepted(self):
        base = len(build_report_link(**REQUIRED | dict(commit="x")))
        url = build_report_link(
            **REQUIRED | dict(commit="x" * (link.MAX_LINK_LENGTH - base + 1))
        )
        self.assertEqual(len(url), link.MAX_LINK_LENGTH)


class BuildFormLinkTest(unittest.TestCase):
    def test_the_form_with_nothing_filled_in(self):
        url = build_form_link()
        self.assertTrue(url.startswith(link.BASE_URL + "?"))
        self.assertEqual(query(url), {"template": ["report.yml"]})


if __name__ == "__main__":
    unittest.main()
