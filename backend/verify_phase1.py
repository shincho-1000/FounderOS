"""
Comprehensive Verification Script for Phase 1.
Tests SQLite ORM persistence & relations + MongoDB Atlas collections.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from app.db.database import init_db, async_session_factory
from app.db.mongo import connect_mongo, close_mongo, get_mongo_db
from app.models.orm import User, Business, Decision


async def run_verification():
    print("=" * 60)
    print("FOUNDER OS - PHASE 1 VERIFICATION")
    print("=" * 60)

    # 1. Initialize SQLite tables
    print("\n[1/3] Checking SQLite schema...")
    await init_db()
    print("  --> SQLite initialized successfully.")

    # 2. Test SQLite CRUD & Foreign Keys
    print("\n[2/3] Testing SQLite ORM CRUD & Relationships...")
    test_user_id = str(uuid.uuid4())
    test_biz_id = str(uuid.uuid4())
    test_dec_id = str(uuid.uuid4())

    async with async_session_factory() as session:
        # Create User
        user = User(
            id=test_user_id,
            email=f"verify_{uuid.uuid4().hex[:6]}@founderos.ai",
            hashed_password="hashed_pw_test",
            full_name="Hackathon Founder",
        )
        session.add(user)
        await session.flush()

        # Create Business linked to User
        biz = Business(
            id=test_biz_id,
            user_id=test_user_id,
            name="FounderOS AI Corp",
            industry="Artificial Intelligence",
            stage="Seed",
            size="1-10",
            description="Autonomous operating system for startup decisions",
            goals="Ship vertical slice in 4.5 hours",
            location="San Francisco, CA",
        )
        session.add(biz)
        await session.flush()

        # Create Decision linked to Business
        dec = Decision(
            id=test_dec_id,
            business_id=test_biz_id,
            question="Should we launch MVP today?",
            context_snapshot={"source": "verification_test", "status": "active"},
            recommendation="Launch immediately to get customer feedback.",
            reasoning="Building a vertical slice validates core assumptions.",
            risks=["Minor edge cases", "Initial load spike"],
            confidence=0.92,
        )
        session.add(dec)
        await session.commit()
        print("  --> User, Business, Decision records written to SQLite.")

    # Read back with joins/relationships
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == test_user_id)
        )
        queried_user = result.scalar_one()
        assert queried_user.email.startswith("verify_")

        biz_result = await session.execute(
            select(Business).where(Business.id == test_biz_id)
        )
        queried_biz = biz_result.scalar_one()
        assert queried_biz.name == "FounderOS AI Corp"

        dec_result = await session.execute(
            select(Decision).where(Decision.id == test_dec_id)
        )
        queried_dec = dec_result.scalar_one()
        assert queried_dec.confidence == 0.92
        assert queried_dec.risks == ["Minor edge cases", "Initial load spike"]
        print("  --> Records successfully retrieved & validated from SQLite.")

        # Cleanup test data (cascade deletes business and decision)
        await session.delete(queried_user)
        await session.commit()
        print("  --> SQLite test data cleaned up.")

    # 3. Test MongoDB Atlas
    print("\n[3/3] Testing MongoDB Atlas connection & collections...")
    await connect_mongo()
    db = get_mongo_db()

    collections = [
        "short_term_memory",
        "long_term_memory",
        "insights",
        "news_cache",
    ]

    for col in collections:
        doc = {
            "business_id": test_biz_id,
            "test_marker": "phase1_verification",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        res = await db[col].insert_one(doc)
        found = await db[col].find_one({"_id": res.inserted_id})
        assert found is not None
        assert found["test_marker"] == "phase1_verification"
        await db[col].delete_one({"_id": res.inserted_id})
        print(f"  --> Collection '{col}': Write + Read + Delete passed.")

    await close_mongo()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! Phase 1 is rock-solid.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_verification())
