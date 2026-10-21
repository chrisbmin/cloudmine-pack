# 07 - Member troubleshooting

What to tell a member, by symptom. The member-facing version of most of this is on the site's install guide
(`https://cloudmine.thecoldnorth.net/mods/install/`).

## The packwiz window shows an error at launch

Usually the internet or GitHub. Ask them to:

1. Check their connection and launch again.
2. If it still fails, click **Cancel** and try again later.

If it fails for everyone, check that `https://raw.githubusercontent.com/chrisbmin/cloudmine-pack/main/pack.toml`
opens in a browser. If it does and members still fail right after a release, the release may have shipped
a file with CRLF line endings or a broken download; check the packwiz window's message and undo with
runbook 06.

## "I want to change my optional mods"

Launch, and click **Optional mods...** in the small packwiz window while it runs. Tick or untick, then
**OK**. The change applies on that launch.

## "I added my own mod and now the game crashes"

Our support line: we support the pack. Ask them to remove or disable their extra mods (right-click the
instance, **Edit**, **Mods**, untick them) and launch again. If it works without their extras, the extra mod
is the problem.

## "Mod mismatch" or "missing mods" when joining

The server and the pack disagree. Either the server window was skipped in a release (runbook 04, step 2),
or the member's sync failed. Check:

1. Their packwiz window finished without errors (ask them to relaunch).
2. The server's `mods/` folder has the shared jars the latest release listed. Re-run
   `python tools/release.py <next version> --dry-run` on a clean `testing` to see what the pack expects.

## "The game says I need a different NeoForge version"

A NeoForge change was released (runbook 05). They change it in Prism: right-click CloudMine, **Edit**,
**Version**, select **NeoForge**, **Change version**, pick the version from the changelog note. Or they can
import the latest starter from the downloads page.

## "I lost my map / settings after switching from the old pack"

Their old Base, Mid or Max instance still has them. Copy `options.txt`, the `xaero` folder and
`screenshots` from the old instance's `minecraft` folder into the new one (install guide, "Moving from an
old Base, Mid or Max pack").
