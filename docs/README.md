# CloudMine pack runbooks

Step-by-step guides for building, testing and releasing the CloudMine modpack. Every command runs in
PowerShell from the repo folder `M:\Code\github\cloudmine-pack` unless a step says otherwise.

| # | Runbook | When |
|---|---|---|
| 01 | [Install the tools](01-install-tools.md) | Once per PC |
| 02 | [Testing setup](02-testing-setup.md) | Once: your testing instance and a test world |
| 03 | [Everyday changes](03-everyday-changes.md) | Adding, updating, removing or re-marking mods |
| 04 | [Release](04-release.md) | Every time you want members to get your changes |
| 05 | [Starter zip](05-starter-zip.md) | Rarely: icon, server list, memory, NeoForge version |
| 06 | [Undo a release](06-undo-a-release.md) | When a release went wrong |
| 07 | [Member troubleshooting](07-member-troubleshooting.md) | When a member asks for help |

## How it fits together

- **`testing` branch:** where you make changes. Only your own testing instance follows it.
- **`main` branch:** what members get. Only `tools/release.py` moves it.
- **Members' instances** run a small program (packwiz-installer) every time they press Play. It reads
  `pack.toml` from `main` on GitHub and downloads whatever changed. Nothing to upload anywhere.
- **The website** (`/mods/` and `/mods/changelog/`) reads `site-data/` from `main`, refreshed within about
  10 minutes of a release.

## Words used here

- **Entry:** one mod, resource pack or shader in the pack. Its id is its file name in `mods/`,
  `resourcepacks/` or `shaderpacks/` without `.pw.toml` (for example `sodium`). `packwiz list` shows them.
- **Shared mod:** a mod that also runs on the server (`side = "both"`). The server must have the exact same
  version, so changing one needs the server step in runbook 04.
- **Client-only:** everything else (`side = "client"`): visual and sound mods, most performance mods,
  shaders, resource packs. No server step.
- **Optional:** a client-only mod members can tick or untick at launch.

## Rules

- Always move to the **latest** version of each mod. If the pack and the server disagree, update the server
  (runbook 04), never downgrade the pack.
- Never edit `main` directly, never force-push.
- Only ship a mod whose license allows it to be downloaded this way; if packwiz says a CurseForge mod needs a
  manual download, don't ship it (runbook 03).
