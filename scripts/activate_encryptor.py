#!/usr/bin/env python3
"""Activate the staged trusted encryptor and its smoke test in Kustomize."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KUSTOMIZATION = ROOT / "deploy" / "k8s" / "kustomization.yaml"
MARKER = "  - smoke-test.yaml\n"
RESOURCES = (
    "  - encryptor.yaml\n",
    "  - encryptor-smoke-test.yaml\n",
)


def activate(kustomization: Path) -> bool:
    source = kustomization.read_text(encoding="utf-8")
    missing = [resource for resource in RESOURCES if resource not in source]
    if not missing:
        return False
    if MARKER not in source:
        raise RuntimeError("could not find the Kustomize resource insertion point")

    updated = source.replace(MARKER, MARKER + "".join(missing), 1)
    kustomization.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kustomization",
        type=Path,
        default=KUSTOMIZATION,
    )
    args = parser.parse_args()

    if activate(args.kustomization):
        print("Activated the trusted encryptor and HTTP-only smoke test.")
    else:
        print("Trusted encryptor resources are already active.")


if __name__ == "__main__":
    main()
