"""Mark a pack entry optional (with its default and description), required, or set which side it's for.

    python tools/mark.py falling-leaves --optional --default on --description "Leaves drift down from trees"
    python tools/mark.py entityculling --required
    python tools/mark.py terralith --side both

The entry id is the .pw.toml file name without the extension (see `packwiz list`). Runs `packwiz refresh` after.
"""
import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))  # so `python tools/mark.py` can import the tools package

from tools.packlib import FOLDERS  # noqa: E402
SIDES = ("client", "both", "server")


def find_entry_file(pack_dir: Path, entry_id: str) -> Path:
    for folder in FOLDERS:
        path = Path(pack_dir) / folder / f"{entry_id}.pw.toml"
        if path.is_file():
            return path
    raise KeyError(entry_id)


def _without_option(text: str) -> str:
    out, skipping = [], False
    for line in text.splitlines():
        if line.strip().startswith("["):
            skipping = line.strip() == "[option]"
        if not skipping:
            out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


def _write(pw: Path, text: str) -> None:
    pw.write_text(text, encoding="utf-8", newline="\n")


def set_option(pw: Path, default: bool, description: str) -> None:
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in description):
        raise ValueError("the description must be one line of plain text (no tabs, line breaks or control characters)")
    text = _without_option(pw.read_text(encoding="utf-8"))
    # json.dumps escapes quotes and backslashes the way TOML does; ensure_ascii=False keeps emoji as-is (TOML has
    # no surrogate-pair escapes).
    block = (f"\n[option]\noptional = true\ndefault = {str(default).lower()}\n"
             f"description = {json.dumps(description, ensure_ascii=False)}\n")
    tomllib.loads(text + block)  # never write a file packwiz couldn't read
    _write(pw, text + block)


def set_required(pw: Path) -> None:
    _write(pw, _without_option(pw.read_text(encoding="utf-8")))


def set_side(pw: Path, side: str) -> None:
    if side not in SIDES:
        raise ValueError(side)
    text = pw.read_text(encoding="utf-8")
    head, sep, rest = text.partition("\n[")
    line = f'side = "{side}"'
    if re.search(r'(?m)^side\s*=', head):
        head = re.sub(r'(?m)^side\s*=.*$', line, head, count=1)
    else:
        head = head.rstrip("\n") + "\n" + line + ("\n" if sep else "")
    _write(pw, head + sep + rest)


def main(argv=None, pack_dir: Path = REPO, run=subprocess.run) -> int:
    p = argparse.ArgumentParser(description="Mark a pack entry optional, required, or set its side.")
    p.add_argument("id", help="entry id: the .pw.toml file name without the extension")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--optional", action="store_true", help="members can turn it on or off at launch")
    mode.add_argument("--required", action="store_true", help="always installed")
    mode.add_argument("--side", choices=SIDES, help="client = members only; both = also on the server")
    p.add_argument("--default", choices=("on", "off"), help="with --optional: ticked by default or not")
    p.add_argument("--description", default="", help="with --optional: one line members see in the checklist")
    args = p.parse_args(argv)
    if args.optional and args.default is None:
        p.error("--optional needs --default on or --default off")

    try:
        pw = find_entry_file(pack_dir, args.id)
    except KeyError:
        print(f"no such entry: {args.id}", file=sys.stderr)
        return 2

    if args.optional:
        try:
            set_option(pw, args.default == "on", args.description)
        except ValueError as e:
            print(f"not changed: {e}", file=sys.stderr)
            return 2
    elif args.required:
        set_required(pw)
    else:
        set_side(pw, args.side)
    run(["packwiz", "refresh"], cwd=pack_dir, check=True)
    print(f"{args.id}: updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
