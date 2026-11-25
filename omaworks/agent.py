"""The agent option: `omaworks report --agent <plugin>`.

See SPEC.md, "The agent option". It starts the user's default coding agent
through Omarchy's omarchy-agent-prompt, with a short prompt that names the
plugin and points at skills/report/SKILL.md. The method lives in that file.

omaworks gives the agent nothing that posts. The agent's last step opens the
filled-in form with `omaworks report`, and the reporter presses Submit.
"""

import os
import shlex

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SKILL = os.path.join(ROOT, "skills", "report", "SKILL.md")
COMMAND = os.path.join(ROOT, "bin", "omaworks")

PROMPT_COMMAND = "omarchy-agent-prompt"


def prompt(plugin, skill=SKILL, command=COMMAND):
    """The prompt the agent starts with."""
    return (
        f"Help me report whether the Omarchy plugin {plugin} works on this "
        "machine's Omarchy version, for omaworks.\n"
        "\n"
        "Read this file and follow its steps. Stop where it says to stop:\n"
        f"  {skill}\n"
        "\n"
        "The omaworks command is:\n"
        f"  {shlex.quote(command)}\n"
        "\n"
        "Never post anything yourself. I check the form and press Submit."
    )


def command_line(plugin, inline, skill=SKILL, command=COMMAND):
    """The omarchy-agent-prompt command line.

    The prompt is one argument: omarchy-agent-prompt joins its arguments
    with spaces anyway. --inline runs the agent in this terminal. Without
    it, the agent opens in its own window.
    """
    args = [PROMPT_COMMAND]
    if inline:
        args.append("--inline")
    args.append(prompt(plugin, skill=skill, command=command))
    return args
