# 01 - Install the tools

Gets your PC ready to work on the pack: Go (which installs packwiz), packwiz itself, Python and git.

**New concepts:**
- **packwiz:** the command-line tool that manages the pack's files. You run it from the repo folder.
- **Go:** the programming language packwiz is written in. You only need it to install and update packwiz.

## Prerequisites

- Windows PowerShell.
- `git` and the GitHub CLI `gh`, signed in as `chrisbmin` (`gh auth status` shows it).

## Steps

### 1. Install Go

```powershell
winget install GoLang.Go
```

Close the PowerShell window and open a new one (so it picks up the new PATH).

```powershell
go version
```

Expected: `go version go1.xx ... windows/amd64`.

### 2. Install packwiz

```powershell
go install github.com/packwiz/packwiz@latest
packwiz --help
```

Expected: `A command line tool for creating Minecraft modpacks` and a list of commands. If it says
`packwiz` is not recognized, open a new PowerShell window; Go puts it in `%USERPROFILE%\go\bin`.

To update packwiz later, run the same `go install` line again.

### 3. Check Python

```powershell
python --version
```

Expected: `Python 3.11` or newer. If it's missing: `winget install Python.Python.3.13`.

### 4. Get the repo

If `M:\Code\github\cloudmine-pack` doesn't exist yet on this PC:

```powershell
cd M:\Code\github
gh repo clone chrisbmin/cloudmine-pack
cd cloudmine-pack
git config core.autocrlf false
git checkout testing
```

`core.autocrlf false` stops git from changing line endings; the pack's file hashes depend on the exact bytes.

## Verify

```powershell
cd M:\Code\github\cloudmine-pack
python -m unittest discover -s tools/tests -t .
packwiz list
```

Expected: `OK` from the tests, and `packwiz list` prints the pack's entries (or nothing yet, before the
first mods are added).

---

## Undo (only if you want to reverse this)

`winget uninstall GoLang.Go`, delete `%USERPROFILE%\go`, and delete the repo folder. Nothing on GitHub changes.
