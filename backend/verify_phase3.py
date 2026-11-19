"""
Verification script for Phase 3: Business Profile.
Covers create / read / update, one-business-per-user, validation,
auth protection, user isolation and the get_current_business dependency.
"""
import asyncio

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.core.dependencies import get_current_business
from app.db.database import async_session_factory, init_db
from app.models.orm.business import Business
from app.models.orm.user import User
from main import app

# Temporary route proving get_current_business works for later phases.
@app.get("/__test__/whoami-business")
async def _whoami(business: Business = Depends(get_current_business)):
    return {"id": business.id, "name": business.name}


EMAILS = ["biz.alice@example.com", "biz.bob@example.com"]
PASSWORD = "SuperSecretPassword123!"


async def cleanup():
    # SQLite does not enforce FK cascades by default, so delete children first.
    async with async_session_factory() as s:
        ids = select(User.id).where(User.email.in_(EMAILS))
        await s.execute(delete(Business).where(Business.user_id.in_(ids)))
        await s.execute(delete(User).where(User.email.in_(EMAILS)))
        await s.commit()


async def register_and_login(client, email, name):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": name},
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def main():
    print("=" * 60)
    print("STARTING PHASE 3 BUSINESS PROFILE VERIFICATION")
    print("=" * 60)
    await init_db()
    await cleanup()

    payload = {
        "name": "  Acme AI  ",
        "industry": "B2B SaaS",
        "stage": "seed",
        "size": "1-10",
        "description": "AI copilots for finance teams",
        "goals": "Reach $50k MRR in 12 months",
        "location": "Bengaluru, India",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        alice = await register_and_login(c, EMAILS[0], "Alice")
        bob = await register_and_login(c, EMAILS[1], "Bob")

        print("\n--- 1. Unauthenticated access is blocked ---")
        for method in ("get", "post", "put"):
            r = await getattr(c, method)("/api/v1/business")
            assert r.status_code == 401, f"{method}: {r.status_code}"
        print("OK: GET/POST/PUT without token -> 401")

        print("\n--- 2. GET before creation -> 404 ---")
        r = await c.get("/api/v1/business", headers=alice)
        assert r.status_code == 404, r.text
        print("OK:", r.json()["detail"])

        print("\n--- 3. get_current_business dependency -> 404 before creation ---")
        r = await c.get("/__test__/whoami-business", headers=alice)
        assert r.status_code == 404, r.text
        print("OK")

        print("\n--- 4. POST validation ---")
        r = await c.post("/api/v1/business", json={"industry": "x"}, headers=alice)
        assert r.status_code == 422, r.text
        r = await c.post(
            "/api/v1/business", json={"name": "   ", "industry": "x"}, headers=alice
        )
        assert r.status_code == 422, r.text
        print("OK: missing/blank required fields rejected (422)")

        print("\n--- 5. POST create business ---")
        r = await c.post("/api/v1/business", json=payload, headers=alice)
        assert r.status_code == 201, r.text
        biz = r.json()
        assert biz["name"] == "Acme AI", "name should be trimmed"
        assert biz["industry"] == "B2B SaaS"
        assert biz["stage"] == "seed" and biz["location"] == "Bengaluru, India"
        assert biz["id"] and biz["user_id"] and biz["created_at"] and biz["updated_at"]
        print("OK: created", biz["id"])

        print("\n--- 6. One business per user (duplicate POST -> 409) ---")
        r = await c.post("/api/v1/business", json=payload, headers=alice)
        assert r.status_code == 409, r.text
        print("OK:", r.json()["detail"])

        print("\n--- 7. GET returns my business ---")
        r = await c.get("/api/v1/business", headers=alice)
        assert r.status_code == 200, r.text
        assert r.json()["id"] == biz["id"]
        print("OK")

        print("\n--- 8. get_current_business dependency resolves ---")
        r = await c.get("/__test__/whoami-business", headers=alice)
        assert r.status_code == 200 and r.json()["id"] == biz["id"], r.text
        print("OK")

        print("\n--- 9. PUT partial update keeps untouched fields ---")
        r = await c.put(
            "/api/v1/business",
            json={"stage": "series-a", "goals": "Reach $200k MRR"},
            headers=alice,
        )
        assert r.status_code == 200, r.text
        up = r.json()
        assert up["stage"] == "series-a" and up["goals"] == "Reach $200k MRR"
        assert up["name"] == "Acme AI" and up["industry"] == "B2B SaaS"
        assert up["location"] == "Bengaluru, India"
        assert up["id"] == biz["id"]
        assert up["updated_at"] >= biz["updated_at"]
        print("OK: stage/goals changed, others preserved")

        print("\n--- 10. PUT can clear an optional field ---")
        r = await c.put("/api/v1/business", json={"description": None}, headers=alice)
        assert r.status_code == 200 and r.json()["description"] is None, r.text
        print("OK")

        print("\n--- 11. PUT rejects blank name / empty body ---")
        r = await c.put("/api/v1/business", json={"name": "  "}, headers=alice)
        assert r.status_code == 422, r.text
        r = await c.put("/api/v1/business", json={}, headers=alice)
        assert r.status_code == 422, r.text
        r = await c.get("/api/v1/business", headers=alice)
        assert r.json()["name"] == "Acme AI"
        print("OK: invalid updates rejected, data intact")

        print("\n--- 12. Data persisted after update (GET) ---")
        r = await c.get("/api/v1/business", headers=alice)
        d = r.json()
        assert d["stage"] == "series-a" and d["description"] is None
        print("OK")

        print("\n--- 13. User isolation ---")
        r = await c.get("/api/v1/business", headers=bob)
        assert r.status_code == 404, "Bob must not see Alice's business"
        r = await c.put("/api/v1/business", json={"name": "Hacked"}, headers=bob)
        assert r.status_code == 404, r.text
        r = await c.post(
            "/api/v1/business",
            json={"name": "Bob Co", "industry": "D2C"},
            headers=bob,
        )
        assert r.status_code == 201 and r.json()["user_id"] != biz["user_id"]
        r = await c.get("/api/v1/business", headers=alice)
        assert r.json()["name"] == "Acme AI"
        print("OK: users are isolated")

        print("\n--- 14. Alias /business works ---")
        r = await c.get("/business", headers=alice)
        assert r.status_code == 200 and r.json()["id"] == biz["id"]
        print("OK")

    await cleanup()
    async with async_session_factory() as s:
        n = (await s.execute(select(func.count()).select_from(Business))).scalar()
        assert n == 0, f"leftover business rows: {n}"
        print(f"\nCleanup done (remaining business rows: {n})")

    print("\n" + "=" * 60)
    print("ALL PHASE 3 TESTS PASSED (14/14)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
