"""Static checks on the workflows. No YAML library: plain text."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "check-report.yml"
BUILD = WORKFLOWS / "build.yml"


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


def permissions(text, indent):
    """Each permissions block at this indent, as sorted "key: value" lines."""
    pad = " " * indent
    blocks = []
    for match in re.finditer(rf"^{pad}permissions:(.*)\n((?:{pad}  .*\n)*)", text, re.M):
        lines = [match.group(1).strip()] if match.group(1).strip() else []
        lines += [line.strip() for line in match.group(2).splitlines()]
        blocks.append(sorted(lines))
    return blocks


def job(text, name):
    """The text of one job under jobs:."""
    match = re.search(rf"^  {name}:\n((?:    .*\n|\n)*)", text, re.M)
    return match.group(1)


class BuildWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.text = BUILD.read_text()

    def test_runs_on_every_change_to_a_report_and_daily(self):
        self.assertIn(
            "issues:\n    types: [opened, edited, closed, reopened, labeled, unlabeled, deleted]",
            self.text,
        )
        self.assertIn("contains(github.event.issue.labels.*.name, 'report')", self.text)
        self.assertIn("github.event.label.name == 'report'", self.text)
        self.assertRegex(self.text, r"schedule:\n    - cron: \"\d+ \d+ \* \* \*\"")
        self.assertIn("workflow_dispatch:", self.text)

    def test_runs_after_each_check(self):
        name = re.search(r"^name: (.*)$", WORKFLOW.read_text(), re.M).group(1)
        self.assertIn(f"workflow_run:\n    workflows: [{name}]\n    types: [completed]", self.text)

    def test_least_permissions(self):
        self.assertEqual(permissions(self.text, 0), [["{}"]])
        self.assertEqual(permissions(job(self.text, "build"), 4), [["contents: read", "issues: read"]])
        self.assertEqual(
            permissions(job(self.text, "deploy"), 4), [["id-token: write", "pages: write"]]
        )
        self.assertEqual(self.text.count("permissions:"), 3)
        self.assertNotIn("write", job(self.text, "build"))

    def test_one_build_at_a_time(self):
        self.assertIn("concurrency:\n  group: build-pages\n  cancel-in-progress: false", self.text)

    def test_builds_and_deploys_the_file(self):
        self.assertIn("- run: python3 -m omaworks.build _site/reports.json", self.text)
        self.assertIn("path: _site", self.text)
        self.assertIn("needs: build", job(self.text, "deploy"))
        self.assertIn("name: github-pages", job(self.text, "deploy"))

    def test_no_expression_inside_run(self):
        blocks = run_blocks(self.text)
        self.assertTrue(blocks)
        for block in blocks:
            self.assertNotIn("${{", block)

    def test_report_text_never_reaches_the_workflow(self):
        for name in ("issue.body", "issue.title", "comment.body", "head_ref", "head_branch"):
            self.assertNotIn(name, self.text)

    def test_only_expressions_it_needs(self):
        expressions = set(re.findall(r"\$\{\{\s*(.*?)\s*\}\}", self.text))
        self.assertEqual(
            expressions, {"secrets.GITHUB_TOKEN", "steps.deployment.outputs.page_url"}
        )

    def test_actions_pinned_like_ci(self):
        ci = set(re.findall(r"uses: (\S+)", (WORKFLOWS / "ci.yml").read_text()))
        ours = set(re.findall(r"uses: (\S+)", self.text))
        pages = {"actions/upload-pages-artifact@v5", "actions/deploy-pages@v5"}
        self.assertLessEqual(pages, ours)
        self.assertLessEqual(ours - pages, ci)
        self.assertIn("actions/checkout@v7", ours)

    def test_checkout_keeps_no_credentials_and_python_is_the_oldest(self):
        self.assertIn("persist-credentials: false", self.text)
        self.assertIn('python-version: "3.11"', self.text)


class RunBlocksTest(unittest.TestCase):
    def test_finds_multi_line_run(self):
        text = "steps:\n  - run: |\n      echo ${{ x }}\n    env:\n      A: b\n"
        self.assertEqual(len(run_blocks(text)), 1)
        self.assertIn("${{ x }}", run_blocks(text)[0])
        self.assertNotIn("A: b", run_blocks(text)[0])

    def test_permissions_finds_inline_and_block_forms(self):
        text = "permissions: {}\njobs:\n  a:\n    permissions:\n      x: read\n    steps:\n"
        self.assertEqual(permissions(text, 0), [["{}"]])
        self.assertEqual(permissions(job(text, "a"), 4), [["x: read"]])


if __name__ == "__main__":
    unittest.main()
