# 02 - Testing setup

Creates your own testing instance in Prism (it follows the `testing` branch, so you see changes before
members do) and a small single-player world for trying out mods.

**New concepts:**
- **Testing instance:** exactly like a member's CloudMine instance, except it reads the pack from the
  `testing` branch. It's named **CloudMine-Testing**.
- **Test world:** a single-player world on your PC. You use it whenever a change touches a shared mod,
  because until you release, your testing instance won't match the live server and can't join it.

## Prerequisites

- Runbook 01 done.
- Prism Launcher installed and signed in.

## Steps

### 1. Build the starter zips

```powershell
cd M:\Code\github\cloudmine-pack
python tools/build_starter.py
```

Expected:

```text
wrote M:\Code\github\cloudmine-pack\dist\CloudMine-Starter.zip
wrote M:\Code\github\cloudmine-pack\dist\CloudMine-Testing.zip
```

### 2. Import the testing instance

In Prism: **Add Instance**, **Import**, **Browse**, pick `dist\CloudMine-Testing.zip`, **OK**.

Expected: an instance called **CloudMine-Testing** with the CloudMine icon.

### 3. First launch

Select it and click **Launch**. A small packwiz window appears and downloads the pack. The first time, it
shows the optional mods checklist; tick what you want to test. Then Minecraft starts.

Expected: the game reaches the title screen; **Multiplayer** lists **CloudMine**.

If the window says it can't find `packwiz-installer-bootstrap.jar`, see "If the pre-launch command fails" in
runbook 05.

### 4. Make the test world

In Minecraft: **Singleplayer**, **Create New World**, name it `Mod Test`, Game Mode **Creative**, then
**Create New World**. Leave it once it loads.

Use this world to try any change that touches a shared mod: place blocks from the mod, open its screens,
walk into new chunks. Delete and recreate it whenever you want a clean slate.

## Verify

- `CloudMine-Testing` launches and shows the packwiz window first.
- The `Mod Test` world loads without errors.
- With no shared changes pending, **Multiplayer**, **CloudMine** joins the live server.

---

## Undo (only if you want to reverse this)

In Prism, right-click **CloudMine-Testing**, **Delete**. Your members are unaffected.
