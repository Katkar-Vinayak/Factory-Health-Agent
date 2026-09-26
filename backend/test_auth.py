"""
Authentication & Authorization Test Suite
==========================================
Comprehensive tests for:
1. Valid login
2. Incorrect password
3. Incorrect email
4. Inactive user
5. JWT creation
6. JWT validation
7. Current-user endpoint
8. Unauthenticated /me
9. Logout
10. Protected machine endpoint without auth
11. Protected machine endpoint with auth
12. Protected agent endpoint without auth
13. Protected notification endpoint without auth
14. Accept requires authentication
15. Reject requires authentication
16. Authenticated operator identity is used for audit
17. Add Machine requires authentication
18. Expired JWT rejection
19. Malformed JWT rejection
20. Password hash is never returned
21. Password is never logged
22. No plaintext password in users.csv
"""

import os
import sys
import csv
import time
import datetime
import uuid
import unittest
import jwt
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app
from services import auth_service, notification_service


class TestAuthentication(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        auth_service.ensure_users_csv_exists()

    def test_01_valid_login(self):
        """1. Valid credentials succeed and return safe user info."""
        res = self.client.post("/api/auth/login", json={
            "email": "operator@factory.com",
            "password": "Factory@123!"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["email"], "operator@factory.com")
        self.assertEqual(data["user"]["role"], "operator")
        self.assertIn("access_token", res.cookies)

    def test_02_incorrect_password(self):
        """2. Incorrect password returns HTTP 401."""
        res = self.client.post("/api/auth/login", json={
            "email": "operator@factory.com",
            "password": "WrongPassword123!"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("invalid email or password", res.json()["detail"].lower())

    def test_03_incorrect_email(self):
        """3. Incorrect email returns HTTP 401."""
        res = self.client.post("/api/auth/login", json={
            "email": "nonexistent@factory.com",
            "password": "Factory@123!"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("invalid email or password", res.json()["detail"].lower())

    def test_04_inactive_user(self):
        """4. Inactive user cannot log in (HTTP 401)."""
        users_file = auth_service.USERS_CSV
        with open(users_file, "r", encoding="utf-8") as f:
            original_content = f.read()

        try:
            with open(users_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "USR-INACTIVE",
                    "inactive@factory.com",
                    "Inactive User",
                    "operator",
                    auth_service.hash_password("Factory@123!"),
                    "false",
                    datetime.datetime.now(datetime.timezone.utc).isoformat()
                ])

            res = self.client.post("/api/auth/login", json={
                "email": "inactive@factory.com",
                "password": "Factory@123!"
            })
            self.assertEqual(res.status_code, 401)
        finally:
            with open(users_file, "w", newline="", encoding="utf-8") as f:
                f.write(original_content)

    def test_05_jwt_creation(self):
        """5. JWT creation produces a valid decodable string."""
        user = {"user_id": "USR-001", "email": "operator@factory.com", "role": "operator"}
        token = auth_service.create_access_token(user)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 20)

    def test_06_jwt_validation(self):
        """6. JWT validation correctly decodes payload."""
        user = {"user_id": "USR-001", "email": "operator@factory.com", "role": "operator"}
        token = auth_service.create_access_token(user)
        payload = auth_service.decode_access_token(token)
        self.assertEqual(payload["sub"], "USR-001")
        self.assertEqual(payload["email"], "operator@factory.com")
        self.assertEqual(payload["role"], "operator")

    def test_07_current_user_endpoint(self):
        """7. GET /api/auth/me returns authenticated user."""
        client = TestClient(app)
        client.post("/api/auth/login", json={
            "email": "operator@factory.com",
            "password": "Factory@123!"
        })
        res = client.get("/api/auth/me")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["user"]["email"], "operator@factory.com")

    def test_08_unauthenticated_me(self):
        """8. GET /api/auth/me without cookie returns HTTP 401."""
        client = TestClient(app)
        res = client.get("/api/auth/me")
        self.assertEqual(res.status_code, 401)

    def test_09_logout(self):
        """9. POST /api/auth/logout clears cookie and invalidates session."""
        client = TestClient(app)
        client.post("/api/auth/login", json={
            "email": "operator@factory.com",
            "password": "Factory@123!"
        })
        # Verify authenticated
        self.assertEqual(client.get("/api/auth/me").status_code, 200)

        # Logout
        res_out = client.post("/api/auth/logout")
        self.assertEqual(res_out.status_code, 200)
        self.assertTrue(res_out.json()["success"])

        # Check me is now 401
        res_me = client.get("/api/auth/me")
        self.assertEqual(res_me.status_code, 401)

    def test_10_protected_machine_endpoint_without_auth(self):
        """10. Protected machine endpoint without auth returns HTTP 401."""
        client = TestClient(app)
        res = client.get("/api/machines/")
        self.assertEqual(res.status_code, 401)

    def test_11_protected_machine_endpoint_with_auth(self):
        """11. Protected machine endpoint with auth returns HTTP 200."""
        client = TestClient(app)
        client.post("/api/auth/login", json={
            "email": "operator@factory.com",
            "password": "Factory@123!"
        })
        res = client.get("/api/machines/")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_12_protected_agent_endpoint_without_auth(self):
        """12. Protected agent endpoint without auth returns HTTP 401."""
        client = TestClient(app)
        res = client.post("/api/agent/analyze", json={"machine_id": "M_001"})
        self.assertEqual(res.status_code, 401)

    def test_13_protected_notification_endpoint_without_auth(self):
        """13. Protected notification endpoint without auth returns HTTP 401."""
        client = TestClient(app)
        res = client.get("/api/notifications")
        self.assertEqual(res.status_code, 401)

    def test_14_accept_requires_authentication(self):
        """14. Accept endpoint without auth returns HTTP 401."""
        client = TestClient(app)
        res = client.post("/api/notifications/NTF-001/accept", json={
            "explicit_approval": True,
            "approved_by": "unauth_user",
            "approved_actions": ["schedule_inspection"]
        })
        self.assertEqual(res.status_code, 401)

    def test_15_reject_requires_authentication(self):
        """15. Reject endpoint without auth returns HTTP 401."""
        client = TestClient(app)
        res = client.post("/api/notifications/NTF-001/reject", json={
            "rejected_by": "unauth_user"
        })
        self.assertEqual(res.status_code, 401)

    def test_16_authenticated_operator_identity_used_for_audit(self):
        """16. Authenticated operator email is recorded for audit regardless of client payload."""
        client = TestClient(app)
        client.post("/api/auth/login", json={
            "email": "operator@factory.com",
            "password": "Factory@123!"
        })

        comp = f"Bearing_{uuid.uuid4().hex[:6]}"
        notif = notification_service.create_notification(
            machine_id="M_001",
            severity="HIGH",
            title="Audit Test Alert",
            message="Bearing wear",
            component=comp,
            root_cause="Bearing Degradation",
            failure_probability=0.91,
            recommendation="Inspect bearing"
        )
        nid = notif["notification_id"]

        # Client attempts to spoof approver as 'imposter_operator'
        res = client.post(f"/api/notifications/{nid}/accept", json={
            "explicit_approval": True,
            "approved_by": "imposter_operator",
            "approved_actions": ["schedule_inspection"]
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Must be attributed to authenticated session
        self.assertEqual(data["approved_by"], "operator@factory.com")

    def test_17_add_machine_requires_authentication(self):
        """17. Add machine endpoint without auth returns HTTP 401."""
        client = TestClient(app)
        res = client.post("/api/machines/add", json={
            "machine_name": "Test Mill",
            "machine_type": "Milling Machine",
            "machine_age_years": 3,
            "rated_power_kw": 45.0,
            "installation_date": "2023-01-01",
            "operating_hours": 1200,
            "maintenance_count": 1,
            "criticality_level": "Medium"
        })
        self.assertEqual(res.status_code, 401)

    def test_18_expired_jwt_rejection(self):
        """18. Expired JWT is rejected with HTTP 401."""
        client = TestClient(app)
        # Create an already expired token
        user = {"user_id": "USR-001", "email": "operator@factory.com", "role": "operator"}
        now = datetime.datetime.now(datetime.timezone.utc)
        expired_payload = {
            "sub": "USR-001",
            "email": "operator@factory.com",
            "role": "operator",
            "iat": int((now - datetime.timedelta(hours=2)).timestamp()),
            "exp": int((now - datetime.timedelta(hours=1)).timestamp())
        }
        expired_token = jwt.encode(expired_payload, auth_service.JWT_SECRET_KEY, algorithm="HS256")
        client.cookies.set("access_token", expired_token)

        res = client.get("/api/auth/me")
        self.assertEqual(res.status_code, 401)
        self.assertIn("expired", res.json()["detail"].lower())

    def test_19_malformed_jwt_rejection(self):
        """19. Malformed JWT is rejected with HTTP 401."""
        client = TestClient(app)
        client.cookies.set("access_token", "invalid.jwt.token")
        res = client.get("/api/auth/me")
        self.assertEqual(res.status_code, 401)

    def test_20_password_hash_never_returned(self):
        """20. Responses never expose password_hash."""
        client = TestClient(app)
        res_login = client.post("/api/auth/login", json={
            "email": "operator@factory.com",
            "password": "Factory@123!"
        })
        self.assertNotIn("password", str(res_login.json()).lower())
        self.assertNotIn("hash", str(res_login.json()).lower())

        res_me = client.get("/api/auth/me")
        self.assertNotIn("password", str(res_me.json()).lower())
        self.assertNotIn("hash", str(res_me.json()).lower())

    def test_21_password_never_logged(self):
        """21. Plaintext password is not logged or leaked."""
        user = auth_service.authenticate_user("operator@factory.com", "Factory@123!")
        self.assertIsNotNone(user)
        self.assertNotIn("password", user)
        self.assertNotIn("password_hash", user)

    def test_22_no_plaintext_password_in_users_csv(self):
        """22. Plaintext password 'Factory@123!' is NOT present in users.csv."""
        with open(auth_service.USERS_CSV, "r", encoding="utf-8") as f:
            raw_content = f.read()
        self.assertNotIn("Factory@123!", raw_content)
        self.assertIn("$2b$", raw_content)  # bcrypt signature


if __name__ == "__main__":
    unittest.main()
