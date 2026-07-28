from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.activate_encryptor import RESOURCES, activate


class ActivateEncryptorTests(unittest.TestCase):
    def test_adds_resources_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "kustomization.yaml"
            path.write_text(
                "resources:\n  - deployment.yaml\n  - smoke-test.yaml\n",
                encoding="utf-8",
            )

            self.assertTrue(activate(path))
            self.assertFalse(activate(path))

            result = path.read_text(encoding="utf-8")
            for resource in RESOURCES:
                self.assertEqual(result.count(resource), 1)


if __name__ == "__main__":
    unittest.main()
