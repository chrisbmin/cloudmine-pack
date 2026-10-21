# 05 - Starter zip

The starter is what members import once. It holds the instance name and icon, memory settings, the
packwiz bootstrap, the server list and a few default options. Mod changes never need a new starter; only
these do:

- a new icon, name or memory setting;
- a new server address;
- a new NeoForge (or Minecraft) version.

**New concepts:**
- **`starter/`:** the source files. `instance.cfg.template` is Prism's instance settings with two
  placeholders, `{{NAME}}` and `{{PACK_URL}}`, filled in by the build.
- **NeoForge version:** packwiz can't change the NeoForge version inside a member's Prism instance. A
  NeoForge change means members change it in Prism themselves (or re-import the starter).

## Prerequisites

- Runbook 01 done.

## Rebuild and upload

1. Edit the files in `starter/`:
   - icon: replace `starter/cloudmine.png` (square PNG, 512x512 is fine);
   - memory: `MaxMemAlloc` in `starter/instance.cfg.template` (in MB);
   - server list: `SERVERS` near the top of `tools/build_starter.py`.
2. Build:

   ```powershell
   python tools/build_starter.py
   ```

3. Test: import `dist\CloudMine-Starter.zip` in Prism as a new instance, launch it, join the server. Delete
   that instance afterwards.
4. Upload `dist\CloudMine-Starter.zip` with FileZilla to MDD
   `public_html/thecoldnorth-cloudmine/dl/CloudMine-Starter.zip` (replace the old one).
5. Commit and push on `testing`:

   ```powershell
   git add starter tools
   git commit -m "Starter: <what changed>"
   git push
   ```

   The starter isn't part of the pack members sync, so this needs no release.

Members who already have the instance keep their old icon and settings; that's fine.

## NeoForge version change

Only when the server moves to a new NeoForge (or a mod needs a newer one).

1. On `testing`, set the version in the pack:

   ```powershell
   packwiz migrate loader 21.1.230
   ```

   (Use the server's new version. Check with `packwiz migrate --help` if the command has changed.)
2. In `starter/mmc-pack.json`, replace every old NeoForge version number with the new one.
3. Rebuild and upload the starter (steps 2 to 4 above).
4. Your testing instance: right-click, **Edit**, **Version**, select **NeoForge**, **Change version**, pick
   the new one.
5. Release (runbook 04) together with the server's NeoForge update, with a note for members:

   ```powershell
   python tools/release.py 2.2.0 --notes "NeoForge is now 21.1.230. In Prism: right-click CloudMine, Edit, Version, NeoForge, Change version, pick 21.1.230."
   ```

## If the pre-launch command fails

If the packwiz window never appears and Prism's log shows the bootstrap jar wasn't found, change the
`PreLaunchCommand` line in `starter/instance.cfg.template` to:

```text
PreLaunchCommand="$INST_JAVA" -jar "$INST_MC_DIR/packwiz-installer-bootstrap.jar" {{PACK_URL}}
```

Rebuild, re-import, re-test, then commit.

## Verify

- A fresh import shows the CloudMine name and icon, syncs on launch, and lists CloudMine under Multiplayer.

---

## Undo (only if you want to reverse this)

`git revert` the starter commit, rebuild, and upload the zip again.
