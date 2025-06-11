import os
import time
import uuid
import unittest

import requests


class TestAPIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Base URL for API (can be overridden via environment)
        port = os.environ.get("PORT", "8001")
        cls.base_url = os.environ.get("API_URL", f"http://localhost:{port}")
        # Ensure container is running and healthy
        for _ in range(15):
            try:
                resp = requests.get(f"{cls.base_url}/health")
                if resp.status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(2)
        raise RuntimeError("API is not healthy or not reachable")

    def test_health(self):
        resp = requests.get(f"{self.base_url}/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "healthy")

    def test_root_and_lang_config(self):
        r = requests.get(f"{self.base_url}/")
        self.assertEqual(r.status_code, 200)
        lr = requests.get(f"{self.base_url}/lang/config")
        self.assertEqual(lr.status_code, 200)

    def test_models_and_auth(self):
        m = requests.get(f"{self.base_url}/models/config")
        self.assertEqual(m.status_code, 200)
        a = requests.get(f"{self.base_url}/auth/status")
        self.assertEqual(a.status_code, 200)
        v = requests.post(f"{self.base_url}/auth/validate", json={"code": ""})
        self.assertEqual(v.status_code, 200)

    def test_export_wiki_endpoints(self):
        pages = [
            {"id": "x1", "title": "T", "content": "C", "filePaths": [], "importance": "low", "relatedPages": []}
        ]
        payload = {"repo_url": "http://x", "pages": pages, "format": "json"}
        jr = requests.post(f"{self.base_url}/export/wiki", json=payload)
        self.assertEqual(jr.status_code, 200)
        md = requests.post(f"{self.base_url}/export/wiki", json={**payload, "format": "markdown"})
        self.assertEqual(md.status_code, 200)

    def test_local_repo_structure_via_container(self):
        # Use the api/config path inside container to verify file listing
        path = "/app/api/config"
        r = requests.get(f"{self.base_url}/local_repo/structure", params={"path": path})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("file_tree", data)

    def test_wiki_cache_and_processed_projects(self):
        owner = f"o{uuid.uuid4().hex[:6]}"
        repo = f"r{uuid.uuid4().hex[:6]}"
        repo_type = "github"
        language = "en"
        # Ensure no existing cache
        g0 = requests.get(f"{self.base_url}/api/wiki_cache", params={"owner": owner, "repo": repo, "repo_type": repo_type, "language": language})
        self.assertEqual(g0.status_code, 200)
        self.assertIsNone(g0.json())
        # Store cache
        ws = {"id": "i", "title": "t", "description": "d", "pages": []}
        payload = {"owner": owner, "repo": repo, "repo_type": repo_type, "language": language, "wiki_structure": ws, "generated_pages": {}}
        p = requests.post(f"{self.base_url}/api/wiki_cache", json=payload)
        self.assertEqual(p.status_code, 200)
        # Check cache exists
        g1 = requests.get(f"{self.base_url}/api/wiki_cache", params={"owner": owner, "repo": repo, "repo_type": repo_type, "language": language})
        self.assertEqual(g1.status_code, 200)
        # Check processed projects
        pp = requests.get(f"{self.base_url}/api/processed_projects")
        self.assertEqual(pp.status_code, 200)
        self.assertTrue(isinstance(pp.json(), list))
        # Cleanup cache
        d = requests.delete(f"{self.base_url}/api/wiki_cache", params={"owner": owner, "repo": repo, "repo_type": repo_type, "language": language})
        self.assertEqual(d.status_code, 200)


if __name__ == "__main__":
    unittest.main()