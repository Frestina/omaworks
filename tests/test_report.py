import unittest

from omaworks.report import parse_body
from tests.fixtures import HOSTILE, body


class ParseBodyTest(unittest.TestCase):
    def test_good_form(self):
        fields = parse_body(body(errors="Panel.qml:41: TypeError: x is null"))
        self.assertEqual(
            fields,
            {
                "plugin": "example.sky-clock",
                "omarchy": "4.5.0-3",
                "commit": "3f2a91c",
                "result": "Works",
                "what": "The clock shows the time.",
                "errors": "Panel.qml:41: TypeError: x is null",
            },
        )

    def test_no_response_is_empty(self):
        self.assertEqual(parse_body(body())["errors"], "")

    def test_windows_line_endings(self):
        fields = parse_body(body().replace("\n", "\r\n"))
        self.assertEqual(fields["plugin"], "example.sky-clock")
        self.assertEqual(fields["result"], "Works")

    def test_missing_heading_is_none(self):
        text = body().replace("### Plugin commit", "### Commit")
        fields = parse_body(text)
        self.assertIsNone(fields["commit"])
        self.assertEqual(fields["omarchy"], "4.5.0-3\n\n### Commit\n\n3f2a91c")

    def test_empty_or_missing_body(self):
        for value in ("", None, 42):
            self.assertEqual(set(parse_body(value).values()), {None})

    def test_heading_in_a_later_field_does_not_replace_an_earlier_one(self):
        text = body(what="### Plugin\n\nexample.moon-phase", errors="### Result\n\nBroken")
        fields = parse_body(text)
        self.assertEqual(fields["plugin"], "example.sky-clock")
        self.assertEqual(fields["result"], "Works")
        self.assertIn("example.moon-phase", fields["what"])

    def test_multiline_value_kept_for_the_checker(self):
        fields = parse_body(body(plugin="example.sky-clock\nexample.moon-phase"))
        self.assertEqual(fields["plugin"], "example.sky-clock\nexample.moon-phase")

    def test_hostile_body_is_kept_as_text(self):
        fields = parse_body(body(**HOSTILE))
        for key in ("plugin", "omarchy", "commit", "result"):
            self.assertEqual(fields[key], HOSTILE[key])
        self.assertEqual(fields["what"], HOSTILE["what"])
        self.assertEqual(fields["errors"], HOSTILE["errors"])


if __name__ == "__main__":
    unittest.main()
