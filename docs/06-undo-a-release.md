# 06 - Undo a release

Puts members back on the previous contents by releasing a new version that reverses the bad change. You
never rewrite `main` or delete tags: members' instances compare against `main`, and a clean new release is
the only change they're guaranteed to pick up.

## Prerequisites

- You know which commit on `testing` caused the problem (`git log --oneline` on `testing`).

## Steps

1. Reverse the change on `testing`:

   ```powershell
   cd M:\Code\github\cloudmine-pack
   git checkout testing
   git pull
   git log --oneline -10
   git revert <commit id of the bad change>
   git push
   ```

   Don't revert the `Release X.Y.Z` commit itself; revert the change commits before it.
2. Test in **CloudMine-Testing** (runbook 03).
3. Release with a new, higher version and a note:

   ```powershell
   python tools/release.py 2.1.1 --dry-run
   python tools/release.py 2.1.1 --notes "Rolled back <what> from 2.1.0."
   ```

   If the reverted change touched shared mods, the dry run lists the server steps; do the server window
   from runbook 04 (put the server's old jars back).

## Verify

- Members' next launch removes or downgrades the bad files (their packwiz window shows it).
- `/mods/changelog/` shows the rollback release.

Never use `git push --force` and never delete a tag.
