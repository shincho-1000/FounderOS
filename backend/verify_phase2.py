"""
Verification script for Phase 2: Authentication & Authorization.
Tests registration, login (JSON & form/OAuth2), /auth/me, invalid credentials,
and duplicate email protection against SQLite.
"""
import asyncio
import sys
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.database import init_db, async_session_factory
from app.models.orm.user import User
from sqlalchemy import select, delete


async def run_phase2_verification():
    print("=" * 60)
    print("🧪 STARTING PHASE 2 AUTH VERIFICATION")
    print("=" * 60)

    # Initialize SQLite tables
    await init_db()
    print("✅ Database tables ensured.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        test_email = "founder.alice@example.com"
        test_password = "SuperSecretPassword123!"
        test_name = "Alice Founder"

        # Cleanup test user if exists from prior run
        async with async_session_factory() as session:
            await session.execute(delete(User).where(User.email == test_email))
            await session.commit()

        # -------------------------------------------------------------
        # 1. Test POST /api/v1/auth/register
        # -------------------------------------------------------------
        print("\n--- 1. Testing Registration (POST /api/v1/auth/register) ---")
        reg_payload = {
            "email": test_email,
            "password": test_password,
            "full_name": test_name,
        }
        res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["email"] == test_email, f"Email mismatch: {data}"
        assert data["full_name"] == test_name, f"Name mismatch: {data}"
        assert "id" in data and data["id"], "User id missing from response"
        assert "created_at" in data, "created_at missing from response"
        assert "password" not in data and "hashed_password" not in data, "Password exposed in response!"
        user_id = data["id"]
        print(f"✅ User registered successfully. ID: {user_id}")

        # -------------------------------------------------------------
        # 2. Test Duplicate Registration (POST /api/v1/auth/register)
        # -------------------------------------------------------------
        print("\n--- 2. Testing Duplicate Registration Prevention ---")
        res_dup = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res_dup.status_code == 400, f"Expected 400 for duplicate email, got {res_dup.status_code}: {res_dup.text}"
        assert "already registered" in res_dup.json().get("detail", "").lower()
        print("✅ Duplicate registration correctly rejected with HTTP 400.")

        # -------------------------------------------------------------
        # 3. Test POST /api/v1/auth/login (JSON Body)
        # -------------------------------------------------------------
        print("\n--- 3. Testing JSON Login (POST /api/v1/auth/login) ---")
        login_payload = {
            "email": test_email,
            "password": test_password,
        }
        res_login = await client.post("/api/v1/auth/login", json=login_payload)
        assert res_login.status_code == 200, f"Expected 200, got {res_login.status_code}: {res_login.text}"
        login_data = res_login.json()
        assert "access_token" in login_data and login_data["access_token"], "access_token missing"
        assert login_data.get("token_type") == "bearer", f"Expected token_type bearer, got: {login_data}"
        access_token = login_data["access_token"]
        print(f"✅ Login successful. Access Token: {access_token[:25]}...")

        # -------------------------------------------------------------
        # 4. Test Login with Wrong Password
        # -------------------------------------------------------------
        print("\n--- 4. Testing Login with Wrong Password ---")
        res_bad_pw = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": "WrongPassword999!"},
        )
        assert res_bad_pw.status_code == 401, f"Expected 401, got {res_bad_pw.status_code}"
        print("✅ Incorrect password rejected with HTTP 401.")

        # -------------------------------------------------------------
        # 5. Test Login with Non-Existent User
        # -------------------------------------------------------------
        print("\n--- 5. Testing Login with Non-Existent User ---")
        res_bad_user = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
        )
        assert res_bad_user.status_code == 401, f"Expected 401, got {res_bad_user.status_code}"
        print("✅ Non-existent user rejected with HTTP 401.")

        # -------------------------------------------------------------
        # 6. Test OAuth2 Form Login (POST /api/v1/auth/token for Swagger UI)
        # -------------------------------------------------------------
        print("\n--- 6. Testing OAuth2 Form Login (POST /api/v1/auth/token) ---")
        res_oauth = await client.post(
            "/api/v1/auth/token",
            data={"username": test_email, "password": test_password},
        )
        assert res_oauth.status_code == 200, f"Expected 200 for OAuth2 form, got {res_oauth.status_code}: {res_oauth.text}"
        oauth_data = res_oauth.json()
        assert "access_token" in oauth_data, "OAuth2 access_token missing"
        assert oauth_data.get("token_type") == "bearer"
        print("✅ Swagger UI OAuth2 form login works properly.")

        # -------------------------------------------------------------
        # 7. Test GET /api/v1/auth/me (Protected Route with Bearer Token)
        # -------------------------------------------------------------
        print("\n--- 7. Testing Authenticated Endpoint (GET /api/v1/auth/me) ---")
        res_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert res_me.status_code == 200, f"Expected 200, got {res_me.status_code}: {res_me.text}"
        me_data = res_me.json()
        assert me_data["id"] == user_id, f"ID mismatch: {me_data}"
        assert me_data["email"] == test_email, f"Email mismatch: {me_data}"
        assert me_data["full_name"] == test_name, f"Full name mismatch: {me_data}"
        print(f"✅ /auth/me returned correct profile for {me_data['email']}.")

        # -------------------------------------------------------------
        # 8. Test Protected Route without Token (Expect 401)
        # -------------------------------------------------------------
        print("\n--- 8. Testing /auth/me without Token ---")
        res_no_auth = await client.get("/api/v1/auth/me")
        assert res_no_auth.status_code == 401, f"Expected 401, got {res_no_auth.status_code}"
        print("✅ Access without token correctly blocked with HTTP 401.")

        # -------------------------------------------------------------
        # 9. Test Protected Route with Invalid Token (Expect 401)
        # -------------------------------------------------------------
        print("\n--- 9. Testing /auth/me with Invalid Token ---")
        res_bad_token = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.payload"},
        )
        assert res_bad_token.status_code == 401, f"Expected 401, got {res_bad_token.status_code}"
        print("✅ Access with invalid token correctly blocked with HTTP 401.")

        # -------------------------------------------------------------
        # 10. Test Compatibility Route (POST /auth/register and /auth/login)
        # -------------------------------------------------------------
        print("\n--- 10. Testing Compatibility Aliases (/auth/me) ---")
        res_compat_me = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert res_compat_me.status_code == 200, f"Expected 200, got {res_compat_me.status_code}"
        print("✅ Backward compatibility route /auth/me operates identically.")

        # Cleanup test user
        async with async_session_factory() as session:
            await session.execute(delete(User).where(User.email == test_email))
            await session.commit()
        print("\n🧹 Test user cleaned up.")

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 2 AUTH TESTS PASSED (10/10)!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_phase2_verification())
