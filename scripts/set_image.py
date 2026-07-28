#!/usr/bin/env python3
"""Set the Docker repository and immutable tag in the Kustomization."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
KUSTOMIZATION = ROOT / "deploy" / "k8s" / "kustomization.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9._/-]*", args.repository):
        parser.error("--repository is not a valid lowercase Docker repository")
    if not re.fullmatch(r"sha-[0-9a-f]{7,40}", args.tag):
        parser.error("--tag must have the form sha-<7-to-40 lowercase hex chars>")

    repository = args.repository
    if not repository.startswith("docker.io/"):
        repository = f"docker.io/{repository}"

    source = KUSTOMIZATION.read_text(encoding="utf-8")
    updated, name_count = re.subn(
        r"(?m)^(\s*-\s+name:\s+).+$",
        rf"\g<1>{repository}",
        source,
        count=1,
    )
    updated, new_name_count = re.subn(
        r"(?m)^(\s+newName:\s+).+$",
        rf"\g<1>{repository}",
        updated,
        count=1,
    )
    updated, tag_count = re.subn(
        r"(?m)^(\s+newTag:\s+).+$",
        rf"\g<1>{args.tag}",
        updated,
        count=1,
    )
    if (name_count, new_name_count, tag_count) != (1, 1, 1):
        raise RuntimeError("could not find the expected Kustomize image fields")

    KUSTOMIZATION.write_text(updated, encoding="utf-8")
    print(f"Promoted {repository}:{args.tag}")


if __name__ == "__main__":
    main()
