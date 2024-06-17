import sqlite3
import unittest

from fastapi.testclient import TestClient

from app.api.acl import acl_router
from script.create_db import init_db

client = TestClient(acl_router)


class TestAPIKeyAccessControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        with sqlite3.connect('test.db') as conn:
            conn.execute("INSERT INTO api_keys (key, api_list, api_limits) VALUES (?, ?, ?)",
                         ("test_key", "/restrictedapi1,/restrictedapi2", "/restrictedapi1:5,/restrictedapi2:10"))

    def test_open_api_access(self):
        response = client.get("/openapi1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "This API is open and doesn't require API key"})

    def test_restricted_api_without_key(self):
        response = client.get("/restrictedapi1")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "API key is missing"})

    def test_restricted_api_with_invalid_key(self):
        response = client.get("/restrictedapi1", headers={"x-api-key": "invalid_key"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "API key does not have access to this API"})

    def test_restricted_api_with_valid_key(self):
        response = client.get("/restrictedapi1", headers={"x-api-key": "test_key"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "This API is restricted and requires a valid API key"})

    def test_restricted_api_usage_limit(self):
        headers = {"x-api-key": "test_key"}
        for _ in range(5):
            response = client.get("/restrictedapi1", headers=headers)
            self.assertEqual(response.status_code, 200)
        response = client.get("/restrictedapi1", headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "API usage limit reached"})


if __name__ == '__main__':
    unittest.main()
