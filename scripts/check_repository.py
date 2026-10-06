"""Offline repository checks; the official HACS/Hassfest jobs remain authoritative."""

import ast
import json
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "sphero_r2d2_ble"


def check(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    components = ROOT / "custom_components"
    domains = sorted(p.name for p in components.iterdir() if p.is_dir() and not p.name.startswith("."))
    check(domains == [DOMAIN], "Expected exactly one integration directory")
    component = components / DOMAIN
    manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
    required = {"domain", "name", "documentation", "issue_tracker", "codeowners", "version"}
    check(required <= manifest.keys(), "Missing HACS integration manifest fields")
    check(manifest["domain"] == DOMAIN, "Manifest domain must match its directory")
    check(manifest["codeowners"] == ["@FutureGUIs"], "Expected the repository owner as codeowner")
    check(list(manifest) == ["domain", "name"] + sorted(set(manifest) - {"domain", "name"}),
          "Manifest order must be domain, name, then alphabetical")
    check(f"## {manifest['version']}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
          "Release version must have a changelog entry")
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    check(set(hacs) == {"name", "homeassistant"}, "Unexpected HACS manifest fields")
    check(hacs["name"] == manifest["name"], "HACS and integration names must match")
    check((ROOT / "README.md").is_file(), "README is required")
    check((component / "config_flow.py").is_file(), "Config flow is required")
    png = (component / "brand" / "icon.png").read_bytes()
    check(png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR", "Brand icon must be PNG")
    check(struct.unpack(">II", png[16:24]) == (256, 256), "Brand icon must be 256x256")
    for path in component.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    for directory in (component, ROOT / "tests", ROOT / "scripts"):
        for path in directory.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
    check("hacs/action@main" in workflow and "home-assistant/actions/hassfest@master" in workflow,
          "Both official validation actions are required")
    check("ignore:" not in workflow, "HACS validation must not ignore checks")
    print(f"Local metadata, brand icon, JSON and Python syntax checks passed for {manifest['version']}")
    print("Official HACS and Hassfest validation must still run on GitHub.")


if __name__ == "__main__":
    main()
