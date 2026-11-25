# omaworks

Does this Omarchy plugin still work on my Omarchy version?

omaworks is a public record of whether each Omarchy plugin works on each Omarchy
version, written by the people who use it. ProtonDB does the same for Steam games
on Linux.

Read the results on the [website](https://frestina.github.io/omaworks/). To see
how it is meant to work, read [SPEC.md](SPEC.md).

## Install

The `omaworks` command opens a report form with your Omarchy version and the
plugin's commit already filled in. Copy these three lines:

```sh
git clone https://github.com/Frestina/omaworks ~/.local/share/omaworks
mkdir -p ~/.local/bin
ln -s ~/.local/share/omaworks/bin/omaworks ~/.local/bin/omaworks
```

Omarchy already has `~/.local/bin` on your PATH. If `omaworks` is already in
there, `ln` stops with an error and changes nothing.

To update:

```sh
git -C ~/.local/share/omaworks pull
```

To remove it:

```sh
rm ~/.local/bin/omaworks
rm -rf ~/.local/share/omaworks
```

## Report

- `omaworks report <plugin>` opens the form with both versions filled in.
- `omaworks report --logs <plugin>` also prints the plugin's error lines from the
  journal, with personal details removed, for you to paste into the form.
- `omaworks report --agent <plugin>` lets your coding agent look into the plugin
  and write a draft. It prints the draft for you to paste into the form.

You can change any word you paste before you press Submit.

Nothing is sent until you press Submit on GitHub.

## Limits

`omaworks report --agent <plugin>` lets your default coding agent look into a
plugin and write a draft for you to paste. Its skill forbids posting, and omaworks gives it no
command that posts. But Omarchy starts agents with their approval prompts off, so
an agent with its own GitHub access could still post if it ignored the skill.

## License

The code is MIT, see [LICENSE](LICENSE). Reports are public and released as CC0
(public domain), so any tool can reuse them.
