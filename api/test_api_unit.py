import os
import json
import tempfile
import shutil
import unittest

from fastapi.testclient import TestClient

import api.api as api_module
from api.config import configs


class TestAPIRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use a temporary directory for wiki cache to avoid polluting real cache
        cls.temp_cache_dir = tempfile.mkdtemp()
        api_module.WIKI_CACHE_DIR = cls.temp_cache_dir
        os.makedirs(api_module.WIKI_CACHE_DIR, exist_ok=True)
        cls.client = TestClient(api_module.app)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_cache_dir)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "deepwiki-api")
        self.assertIn("timestamp", data)

    def test_root_endpoints_listed(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("version", data)
        self.assertIn("endpoints", data)
        # Check that health endpoint is listed
        endpoints = [e for group in data["endpoints"].values() for e in group]
        self.assertIn("GET /health", endpoints)

    def test_lang_config(self):
        response = self.client.get("/lang/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("supported_languages", data)
        self.assertIn("default", data)
        # default matches config
        self.assertEqual(data["default"], configs["lang_config"]["default"])

    def test_auth_status_and_validate(self):
        # auth status should reflect WIKI_AUTH_MODE
        status_resp = self.client.get("/auth/status")
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertIn("auth_required", status_data)
        # validate default code (empty) is successful when no auth mode
        validate_resp = self.client.post("/auth/validate", json={"code": ""})
        self.assertEqual(validate_resp.status_code, 200)
        self.assertTrue(validate_resp.json().get("success"))
        # invalid code yields success=False
        bad_resp = self.client.post("/auth/validate", json={"code": "wrong"})
        self.assertEqual(bad_resp.status_code, 200)
        self.assertFalse(bad_resp.json().get("success"))

    def test_models_config(self):
        response = self.client.get("/models/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("providers", data)
        self.assertIn("defaultProvider", data)
        self.assertEqual(data["defaultProvider"], configs.get("default_provider"))

    def test_export_wiki_json_and_markdown(self):
        pages = [
            {
                "id": "p1",
                "title": "Page One",
                "content": "Content of page one.",
                "filePaths": ["file1.py"],
                "importance": "high",
                "relatedPages": []
            }
        ]
        base = {"repo_url": "https://example.com/repo", "pages": pages}
        # JSON export
        json_payload = {"format": "json", **base}
        json_resp = self.client.post("/export/wiki", json=json_payload)
        self.assertEqual(json_resp.status_code, 200)
        self.assertEqual(json_resp.headers["content-type"].split(";")[0], "application/json")
        self.assertIn("Content-Disposition", json_resp.headers)
        body = json_resp.json()
        self.assertEqual(body.get("metadata", {}).get("repository"), base["repo_url"])
        self.assertEqual(body.get("metadata", {}).get("page_count"), len(pages))
        # Markdown export
        md_payload = {"format": "markdown", **base}
        md_resp = self.client.post("/export/wiki", json=md_payload)
        self.assertEqual(md_resp.status_code, 200)
        self.assertEqual(md_resp.headers["content-type"].split(";")[0], "text/markdown")
        self.assertIn("Content-Disposition", md_resp.headers)
        text = md_resp.text
        self.assertTrue(text.startswith(f"# Wiki Documentation for {base['repo_url']}"))

    def test_local_repo_structure_missing_and_not_found(self):
        # Missing 'path' should return 400
        no_path = self.client.get("/local_repo/structure")
        self.assertEqual(no_path.status_code, 400)
        # Not found path should return 404
        nf = self.client.get("/local_repo/structure", params={"path": "/does/not/exist"})
        self.assertEqual(nf.status_code, 404)

    def test_local_repo_structure_success(self):
        # Create a temp directory with files and a README.md
        temp_dir = tempfile.mkdtemp()
        readme = os.path.join(temp_dir, "README.md")
        with open(readme, "w", encoding="utf-8") as f:
            f.write("Hello")
        extra = os.path.join(temp_dir, "test.txt")
        with open(extra, "w", encoding="utf-8") as f:
            f.write("World")
        resp = self.client.get("/local_repo/structure", params={"path": temp_dir})
        shutil.rmtree(temp_dir)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("file_tree", data)
        self.assertIn("readme", data)
        self.assertIn("test.txt", data["file_tree"])
        self.assertEqual(data["readme"], "Hello")

    def test_wiki_cache_crud_and_processed_projects(self):
        owner = "o"
        repo = "r"
        repo_type = "github"
        language = "en"
        # initial cache get should be None
        get_resp = self.client.get("/api/wiki_cache", params={"owner": owner, "repo": repo, "repo_type": repo_type, "language": language})
        self.assertEqual(get_resp.status_code, 200)
        self.assertIsNone(get_resp.json())
        # store cache
        wiki_structure = {"id": "w1", "title": "Title", "description": "Desc", "pages": []}
        store_payload = {"owner": owner, "repo": repo, "repo_type": repo_type, "language": language, "wiki_structure": wiki_structure, "generated_pages": {}}
        store_resp = self.client.post("/api/wiki_cache", json=store_payload)
        self.assertEqual(store_resp.status_code, 200)
        self.assertIn("message", store_resp.json())
        # get cache now returns data
        get2 = self.client.get("/api/wiki_cache", params={"owner": owner, "repo": repo, "repo_type": repo_type, "language": language})
        self.assertEqual(get2.status_code, 200)
        data2 = get2.json()
        self.assertEqual(data2["wiki_structure"]["id"], "w1")
        # processed projects should list one entry
        proc = self.client.get("/api/processed_projects")
        self.assertEqual(proc.status_code, 200)
        list_proc = proc.json()
        self.assertTrue(isinstance(list_proc, list))
        self.assertEqual(len(list_proc), 1)
        entry = list_proc[0]
        expected_id = f"deepwiki_cache_{repo_type}_{owner}_{repo}_{language}.json"
        self.assertEqual(entry.get("id"), expected_id)
        # delete cache
        del_resp = self.client.delete("/api/wiki_cache", params={"owner": owner, "repo": repo, "repo_type": repo_type, "language": language})
        self.assertEqual(del_resp.status_code, 200)
        self.assertIn("message", del_resp.json())
        # get cache again is None
        get3 = self.client.get("/api/wiki_cache", params={"owner": owner, "repo": repo, "repo_type": repo_type, "language": language})
        self.assertEqual(get3.status_code, 200)
        self.assertIsNone(get3.json())


if __name__ == "__main__":
    unittest.main()