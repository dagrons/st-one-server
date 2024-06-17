import unittest
from fastapi.testclient import TestClient

from app.api.main import app


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_public_api(self):
        response = self.client.get("/public-api")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "This is a public API"})

    def test_private_api_without_key(self):
        response = self.client.get("/private-api")
        self.assertEqual(response.status_code, 403)

    def test_generate_api_key(self):
        response = self.client.post("/auth/generate-api-key")
        self.assertEqual(response.status_code, 200)
        api_key = response.json().get("api_key")
        self.assertIsNotNone(api_key)

        response = self.client.get(f"/private-api?api_key={api_key}")
        self.assertEqual(response.status_code, 403)

    def test_set_api_access(self):
        response = self.client.post("/auth/generate-api-key")
        self.assertEqual(response.status_code, 200)
        api_key = response.json().get("api_key")
        self.assertIsNotNone(api_key)

        response = self.client.post("/auth/set-api-access", json={"key": api_key, "api_name": "private-api", "access_limit": 5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Access limit set successfully"})

        for _ in range(5):
            response = self.client.get(f"/private-api?api_key={api_key}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"message": "This is a private API"})

        response = self.client.get(f"/private-api?api_key={api_key}")
        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
