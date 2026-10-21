# 04 - Release

Sends what's on `testing` to every member. Members get it the next time they press Play; the website's
Mods page and changelog update within about 10 minutes.

**New concepts:**
- **Version:** three numbers, like `2.1.0`. Bump the last number for small updates (`2.1.0` -> `2.1.1`),
  the middle one for bigger changes (`2.1.1` -> `2.2.0`). Each version can only be released once.
- **Server window:** when a release changes shared mods, the server must get the same jars at the same
  time. You stop the server, swap its jars, release, then start it.

## Prerequisites

- Your changes are committed and pushed to `testing` and you've tested them (runbook 03).
- You're on `testing` with a clean tree: `git status` says `nothing to commit, working tree clean`.

## Steps

### 1. Dry run

```powershell
cd M:\Code\github\cloudmine-pack
python tools/release.py 2.1.0 --dry-run
```

Expected: a summary like `CloudMine 2.1.0: 1 added, 3 updated, 0 removed`, one line per change, and
`Dry run: nothing changed.`

If it says `Not released: ...`, fix what it says (wrong branch, uncommitted changes, version already
used, CRLF line endings) and run it again.

If the output includes **"This release changes mods that also run on the SERVER"**, follow step 2.
Otherwise skip to step 3.

### 2. Server window (only for shared changes)

Keep the dry-run output open; it lists exactly which jars to delete and which to upload, with download links.

1. Tell anyone online that the server is restarting for a few minutes.
2. Crafty (`https://crafty.cloudmine.thecoldnorth.net`), the CloudMine server, **Backups**: take a backup
   and wait for it to finish.
3. **Stop** the server and wait until it shows stopped.
4. Download each jar the dry run lists under "Upload these jars" (click each link).
5. Crafty, **Files**, open `mods/`:
   - delete each jar listed under "Delete these jars";
   - upload each jar you downloaded.
   Files uploaded through Crafty are already owned correctly. (If you copy them in another way, run
   `sudo chown 1000:0 <files>` on the VM.)
6. Leave the server stopped.

### 3. Release

```powershell
python tools/release.py 2.1.0 --notes "One sentence for the changelog, optional"
```

If it shows the server steps again, type `stopped` and press Enter (you did them in step 2).

Expected, at the end:

```text
Released CloudMine 2.1.0. Members get it the next time they press Play.
```

(plus `Now start the server in Crafty and join to confirm.` when there were server steps).

Use `--notes` when members need to know something, for example a NeoForge change (runbook 05).

### 4. Start the server (only if you stopped it)

Crafty, **Start**. Watch the console (or `logs/latest.log`) until it says `Done`. If it stops with an error
about a mod, see Undo.

## Verify

1. Launch **CloudMine-Testing**: it downloads nothing new (testing and main are now the same) and joins the
   live server.
2. On GitHub, `https://github.com/chrisbmin/cloudmine-pack/tags` shows `v2.1.0`.
3. After about 10 minutes: `https://cloudmine.thecoldnorth.net/mods/` shows `Version 2.1.0`, and
   `https://cloudmine.thecoldnorth.net/mods/changelog/` has the new release at the top.

---

## Undo (only if you want to reverse this)

```text
STOP. Only if the release broke something.
```

- **Server won't start after the swap:** stop it, restore the Crafty backup from step 2 (Backups, restore),
  start it. Then undo the pack change with runbook 06 so members match the server again.
- **Pack problem only:** runbook 06.
