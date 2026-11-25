"""Static checks on the report-checking workflow. No YAML library: plain text."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "check-report.yml"


def run_blocks(text):
    """The text of every run: step, including a multi-line one."""
    blocks = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        match = re.match(r"^(\s*)(- )?run:(.*)$", line)
        if not match:
            continue
        # The column of "run" itself; its sibling keys start there too.
        indent = len(match.group(1)) + len(match.group(2) or "")
        block = [match.group(3)]
        for following in lines[i + 1 :]:
            if following.strip() and len(following) - len(following.lstrip()) <= indent:
                break
            block.append(following)
        blocks.append("\n".join(block))
    return blocks


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text()

    def test_runs_on_report_opened_or_edited(self):
        self.assertIn("issues:\n    types: [opened, edited]", self.text)
        self.assertIn("contains(github.event.issue.labels.*.name, 'report')", self.text)

    def test_permissions_are_issues_write_and_contents_read_only(self):
        block = re.search(r"^permissions:\n((?:  .*\n)+)", self.text, re.M).group(1)
        self.assertEqual(
            sorted(line.strip() for line in block.splitlines()),
            ["contents: read", "issues: write"],
        )
        self.assertEqual(self.text.count("permissions:"), 1)

    def test_no_expression_inside_run(self):
        blocks = run_blocks(self.text)
        self.assertTrue(blocks)
        for block in blocks:
            self.assertNotIn("${{", block)

    def test_report_text_never_reaches_the_workflow(self):
        for name in ("issue.body", "issue.title", "comment.body", "head_ref"):
            self.assertNotIn(name, self.text)

    def test_only_expressions_it_needs(self):
        expressions = set(re.findall(r"\$\{\{\s*(.*?)\s*\}\}", self.text))
        self.assertEqual(expressions, {"github.event.issue.number", "secrets.GITHUB_TOKEN"})

    def test_actions_pinned_like_ci(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        ours = set(re.findall(r"uses: (\S+)", self.text))
        self.assertTrue(ours)
        self.assertLessEqual(ours, set(re.findall(r"uses: (\S+)", ci)))

    def test_checkout_keeps_no_credentials(self):
        self.assertIn("persist-credentials: false", self.text)


class RunBlocksTest(unittest.TestCase):
    def test_finds_multi_line_run(self):
        text = "steps:\n  - run: |\n      echo ${{ x }}\n    env:\n      A: b\n"
        self.assertEqual(len(run_blocks(text)), 1)
        self.assertIn("${{ x }}", run_blocks(text)[0])
        self.assertNotIn("A: b", run_blocks(text)[0])


if __name__ == "__main__":
    unittest.main()
