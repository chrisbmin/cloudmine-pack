# CloudMine modpack

The client modpack for the CloudMine Minecraft server (Minecraft 1.21.1, NeoForge), built with
[packwiz](https://packwiz.infra.link/) and played through [Prism Launcher](https://prismlauncher.org/).

Members never touch this repo. They import the CloudMine starter once from
<https://cloudmine.thecoldnorth.net/mods/download/>, and the pack keeps itself up to date every time
they press Play.

We support the pack. If something breaks, turn off your extras first.

## Pack URLs

- Members (`main`): `https://raw.githubusercontent.com/chrisbmin/cloudmine-pack/main/pack.toml`
- Owner testing (`testing`): `https://raw.githubusercontent.com/chrisbmin/cloudmine-pack/testing/pack.toml`

## What's in here

- `pack.toml`, `index.toml`, `mods/`, `resourcepacks/`, `shaderpacks/`, `config/`: the pack itself.
- `tools/`: Python helpers (`mark.py`, `release.py`, `build_starter.py`, `migrate.py`).
- `starter/`: source for the one-time Prism starter instance.
- `site-data/`: data the CloudMine website reads (written by `release.py`).
- `docs/`: runbooks, starting with `docs/README.md`.

Tests: `python -m unittest discover -s tools/tests -t .`
