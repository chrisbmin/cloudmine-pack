"""Build the one-time Prism starter instances from starter/.

    python tools/build_starter.py

Writes dist/CloudMine-ModPack.zip (members, follows main) and dist/CloudMine-Testing.zip (owner, follows
testing). Each holds the instance settings, the CloudMine icon, the packwiz bootstrap that syncs the pack on
every launch, a server list with CloudMine in it, and a few default options.
"""
import struct
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/chrisbmin/cloudmine-pack"
SERVERS = [("CloudMine", "play.cloudmine.thecoldnorth.net")]
STARTERS = [("CloudMine-ModPack.zip", "CloudMine", f"{RAW}/main/pack.toml"),
            ("CloudMine-Testing.zip", "CloudMine-Testing", f"{RAW}/testing/pack.toml")]


def _nbt_string(s: str) -> bytes:
    data = s.encode("utf-8")
    return struct.pack(">H", len(data)) + data


def servers_dat(servers: list[tuple[str, str]]) -> bytes:
    """Minecraft's uncompressed servers.dat NBT: {servers: [{name, ip}, ...]}."""
    out = b"\x0a" + _nbt_string("")  # root compound
    out += b"\x09" + _nbt_string("servers") + b"\x0a" + struct.pack(">i", len(servers))
    for name, ip in servers:
        out += b"\x08" + _nbt_string("name") + _nbt_string(name)
        out += b"\x08" + _nbt_string("ip") + _nbt_string(ip)
        out += b"\x00"  # end of this server's compound
    return out + b"\x00"  # end of root


def render_cfg(template: str, name: str, pack_url: str) -> str:
    return template.replace("{{NAME}}", name).replace("{{PACK_URL}}", pack_url)


def build(starter_dir: Path, out_zip: Path, name: str, pack_url: str) -> None:
    starter_dir = Path(starter_dir)
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    cfg = render_cfg((starter_dir / "instance.cfg.template").read_text(encoding="utf-8"), name, pack_url)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("instance.cfg", cfg)
        z.write(starter_dir / "mmc-pack.json", "mmc-pack.json")
        z.write(starter_dir / "cloudmine.png", "cloudmine.png")
        z.write(starter_dir / "packwiz-installer-bootstrap.jar", "minecraft/packwiz-installer-bootstrap.jar")
        z.writestr("minecraft/servers.dat", servers_dat(SERVERS))
        z.write(starter_dir / "options.txt", "minecraft/options.txt")


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    for filename, name, url in STARTERS:
        out = REPO / "dist" / filename
        build(REPO / "starter", out, name, url)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
