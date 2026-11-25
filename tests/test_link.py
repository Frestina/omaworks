import unittest
from urllib.parse import parse_qs, urlsplit

from omaworks import link
from omaworks.link import LinkError, LinkTooLong, build_report_link

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
                "plugin": ["example.sky-clock"],
                "omarchy": ["4.5.0-3"],
                "commit": ["3f2a91c"],
            },
        )

    def test_spaces_are_percent_20_not_plus(self):
        url = build_report_link(**REQUIRED, what="a b")
        self.assertIn("what=a%20b", url)
        self.assertNotIn("+", url)

    def test_ampersand_does_not_split_a_value(self):
        url = build_report_link(**REQUIRED, what="a&b=c")
        self.assertIn("what=a%26b%3Dc", url)
        self.assertEqual(query(url)["what"], ["a&b=c"])

    def test_hash_does_not_start_a_fragment(self):
        url = build_report_link(**REQUIRED, what="see #12")
        self.assertNotIn("#", url)
        self.assertEqual(query(url)["what"], ["see #12"])

    def test_newlines_are_encoded(self):
        url = build_report_link(**REQUIRED, errors="one\ntwo")
        self.assertIn("errors=one%0Atwo", url)
        self.assertNotIn("\n", url)

    def test_non_ascii_is_utf8_percent_encoded(self):
        url = build_report_link(**REQUIRED, what="café")
        self.assertIn("what=caf%C3%A9", url)
        self.assertTrue(url.isascii())

    def test_optional_fields_left_out_when_missing_or_empty(self):
        url = build_report_link(**REQUIRED, result="", what=None, errors="  ")
        self.assertEqual(
            set(query(url)), {"template", "plugin", "omarchy", "commit"}
        )

    def test_optional_fields_included_when_given(self):
        url = build_report_link(
            **REQUIRED, result="Works with problems", what="w", errors="e"
        )
        q = query(url)
        self.assertEqual(q["result"], ["Works with problems"])
        self.assertEqual(q["what"], ["w"])
        self.assertEqual(q["errors"], ["e"])

    def test_unknown_result_refused(self):
        with self.assertRaises(LinkError):
            build_report_link(**REQUIRED, result="Fine")

    def test_required_fields_refused_when_empty(self):
        for name in REQUIRED:
            with self.subTest(name=name):
                args = dict(REQUIRED, **{name: " "})
                with self.assertRaises(LinkError):
                    build_report_link(**args)

    def test_too_long_link_refused(self):
        with self.assertRaises(LinkTooLong):
            build_report_link(**REQUIRED, errors="x" * link.MAX_LINK_LENGTH)

    def test_length_counts_the_encoded_link(self):
        # Short as text, long once every newline becomes %0A.
        with self.assertRaises(LinkTooLong):
            build_report_link(**REQUIRED, errors="a\n" * (link.MAX_LINK_LENGTH // 4))

    def test_link_just_under_the_limit_is_accepted(self):
        base = len(build_report_link(**REQUIRED, errors="x"))
        url = build_report_link(
            **REQUIRED, errors="x" * (link.MAX_LINK_LENGTH - base + 1)
        )
        self.assertEqual(len(url), link.MAX_LINK_LENGTH)


if __name__ == "__main__":
    unittest.main()
