#!/usr/bin/env python3
"""Set the Docker repository and tag in the Kustomization."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
KUSTOMIZATION = ROOT / "deploy" / "k8s" / "kustomization.yaml"


def normalize_repository(repository: str) -> str:
    """Return a Docker repository, preserving explicit registry host:port."""
    if "://" in repository or "@" in repository:
        raise ValueError("repository must not contain a URL scheme or digest")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9._:/-]*[a-z0-9])?", repository):
        raise ValueError("repository is not a valid lowercase Docker repository")

    first_component = repository.split("/", 1)[0]
    if (
        "." not in first_component
        and ":" not in first_component
        and first_component != "localhost"
    ):
        return f"docker.io/{repository}"
    return repository


def set_image(kustomization: Path, repository: str, tag: str) -> str:
    """Update only the Kustomize replacement image and tag."""
    repository = normalize_repository(repository)
    if tag != "latest" and not re.fullmatch(r"sha-[0-9a-f]{7,40}", tag):
        raise ValueError(
            "tag must be latest or have the form "
            "sha-<7-to-40 lowercase hex chars>"
        )

    source = kustomization.read_text(encoding="utf-8")
    updated, new_name_count = re.subn(
        r"(?m)^(\s+newName:\s+).+$",
        rf"\g<1>{repository}",
        source,
        count=1,
    )
    updated, tag_count = re.subn(
        r"(?m)^(\s+newTag:\s+).+$",
        rf"\g<1>{tag}",
        updated,
        count=1,
    )
    if (new_name_count, tag_count) != (1, 1):
        raise RuntimeError("could not find the expected Kustomize image fields")

    kustomization.write_text(updated, encoding="utf-8")
    return repository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    try:
        repository = set_image(KUSTOMIZATION, args.repository, args.tag)
    except ValueError as error:
        parser.error(str(error))
    print(f"Promoted {repository}:{args.tag}")


if __name__ == "__main__":
    main()
