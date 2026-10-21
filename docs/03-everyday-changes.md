# 03 - Everyday changes

Adding, updating, removing and re-marking mods, resource packs and shaders. All of it happens on the
`testing` branch; members see nothing until you release (runbook 04).

**New concepts:**
- **`packwiz refresh`:** re-writes `index.toml`, the list of every file and its hash. The tools here run it
  for you; run it yourself after editing files by hand.
- **Push to `testing`:** your testing instance reads from GitHub, so a change only reaches it after
  `git push`.

## Prerequisites

- Runbooks 01 and 02 done.

## Start every session

```powershell
cd M:\Code\github\cloudmine-pack
git checkout testing
git pull
```

## Routine upkeep: update everything

The rule is always the latest version of every mod.

```powershell
packwiz update --all
```

Expected: a list of updated entries, or `All files are already up to date!`. Then check which kind of
change it is:

```powershell
git diff --stat
```

If any of the changed files is a shared mod (`side = "both"` inside the file), this is a **shared change**:
test in the single-player world, and the release will need the server step. `python tools/release.py
X.Y.Z --dry-run` (runbook 04) tells you for certain.

## Add a mod, resource pack or shader

From Modrinth (preferred). Use the slug from the Modrinth page address, for example
`https://modrinth.com/mod/sodium` has the slug `sodium`:

```powershell
packwiz modrinth add sodium
```

packwiz picks the newest version for Minecraft 1.21.1 and NeoForge, adds any libraries it needs, and puts
resource packs and shaders in the right folders. If it asks a question, the default answer is usually right.

Then decide what it is:

- **A visual, sound or convenience extra:** make it optional:

  ```powershell
  python tools/mark.py <id> --optional --default off --description "One line saying what members notice"
  ```

  Use `--default on` for light, safe extras most people would want.
- **Needed on the server too** (it adds blocks, items, mobs or world generation): mark it shared, and
  install the same jar on the server at release time:

  ```powershell
  python tools/mark.py <id> --side both
  ```
- **Everything else that's client-only** (performance, HUD):

  ```powershell
  python tools/mark.py <id> --side client
  ```

`<id>` is the entry's file name without `.pw.toml`; `packwiz list` shows them.

From CurseForge, only when it isn't on Modrinth:

```powershell
packwiz curseforge add <slug>
```

If packwiz says the author has disabled third-party downloads or asks you to download the file manually,
**don't ship it**: remove it again (`packwiz remove <id>`) and pick an alternative. Members would be stuck
with a manual download.

packwiz doesn't always warn. After adding anything from CurseForge, push and launch **CloudMine-Testing**:
if a **"Failed file downloads"** window lists it, the author blocks third-party downloads. Remove it and use
a Modrinth alternative (this is why WI Zoom was swapped for Just Zoom).

## Update one entry

```powershell
packwiz update <id>
```

## Remove an entry

```powershell
packwiz remove <id>
```

Removing a shared mod also means removing it from the server at release time; the release tool lists it.
Be careful with mods whose blocks are already placed in the world (for example Refurbished Furniture):
removing those from the server deletes the blocks.

## Change how an entry is marked

```powershell
python tools/mark.py <id> --optional --default on --description "Text"
python tools/mark.py <id> --required
python tools/mark.py <id> --side client
python tools/mark.py <id> --side both
```

Expected: `<id>: updated`. Run it once per change you want (optional/required, then side).

## Ship a config file

Put it at the same path it has inside an instance's `minecraft` folder, for example
`config/maplink/general.json5`, then:

```powershell
packwiz refresh
```

A config shipped this way replaces the member's copy whenever you change it. Save it with Unix (LF) line
endings (VS Code: click `CRLF` in the status bar, choose `LF`); the release refuses CRLF files.

## Save and test

```powershell
git add -A
git commit -m "Add sodium"
git push
```

Then launch **CloudMine-Testing**:

- **Client-only change:** play on the live server as normal.
- **Shared change:** play in the `Mod Test` single-player world (runbook 02). The live server won't let you
  in until the release swaps its jars.

Happy with it? Release it (runbook 04). Not happy? Undo it on `testing`:

```powershell
git revert HEAD
git push
```

## Verify

- `packwiz list` shows the change.
- `git status` is clean after committing.
- The testing instance downloads the change on its next launch.
