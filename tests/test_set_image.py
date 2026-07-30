import tempfile
from pathlib import Path
import unittest

from scripts.set_image import normalize_repository, set_image


KUSTOMIZATION = """\
images:
  - name: docker.io/dockerboi99/he_k8s
    newName: docker.io/dockerboi99/he_k8s
    newTag: latest
"""


class SetImageTests(unittest.TestCase):
    def test_explicit_registry_host_and_port_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "kustomization.yaml"
            path.write_text(KUSTOMIZATION, encoding="utf-8")

            repository = set_image(
                path,
                "hub.vtcc.vn:8989/dockerboi99/he_k8s",
                "sha-1234567",
            )

            self.assertEqual(
                repository, "hub.vtcc.vn:8989/dockerboi99/he_k8s"
            )
            result = path.read_text(encoding="utf-8")
            self.assertIn(
                "name: docker.io/dockerboi99/he_k8s",
                result,
            )
            self.assertIn(
                "newName: hub.vtcc.vn:8989/dockerboi99/he_k8s",
                result,
            )
            self.assertIn("newTag: sha-1234567", result)

    def test_unqualified_repository_uses_docker_hub(self):
        self.assertEqual(
            normalize_repository("dockerboi99/he_k8s"),
            "docker.io/dockerboi99/he_k8s",
        )

    def test_repository_url_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_repository("https://hub.example/he_k8s")


if __name__ == "__main__":
    unittest.main()
