"""Seed data for development/testing."""
import asyncio
import uuid
from datetime import date, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.db.database import async_session_factory, engine
from app.db.base import Base
from app.models.orm.user import User
from app.models.orm.site import Site
from app.models.orm.item import Item
from app.models.orm.policy import NutritionPolicy, AllergenPolicy
from app.models.orm.recipe import Recipe
from app.models.orm.menu_plan import MenuPlan, MenuPlanItem
from app.models.orm.haccp import HaccpChecklist

# Fixed UUIDs for deterministic seed
SITE_1_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SITE_2_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000001001")
NUT_ID = uuid.UUID("00000000-0000-0000-0000-000000001002")
KIT_ID = uuid.UUID("00000000-0000-0000-0000-000000001003")
QLT_ID = uuid.UUID("00000000-0000-0000-0000-000000001004")
POLICY_1_ID = uuid.UUID("00000000-0000-0000-0000-000000002001")
ALLERGEN_POLICY_1_ID = uuid.UUID("00000000-0000-0000-0000-000000002002")


async def seed():
    """Insert seed data if tables are empty."""
    async with async_session_factory() as db:
        # Check if already seeded
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("[seed] Data already exists, skipping.")
            return

        print("[seed] Inserting seed data...")

        # ── Sites ──
        site1 = Site(
            id=SITE_1_ID,
            name="SmallSF Gangnam Center",
            type="office",
            capacity=400,
            address="Seoul, Gangnam-gu",
            operating_hours={"weekday": {"start": "07:00", "end": "19:00"}},
            is_active=True,
        )
        site2 = Site(
            id=SITE_2_ID,
            name="SmallSF Pangyo Lab",
            type="factory",
            capacity=200,
            address="Seongnam, Bundang-gu",
            operating_hours={"weekday": {"start": "06:00", "end": "20:00"}},
            is_active=True,
        )
        db.add_all([site1, site2])
        await db.flush()

        # ── Users ──
        users = [
            User(
                id=ADMIN_ID, email="admin@smallsf.com", name="Admin",
                hashed_password=hash_password("admin1234"),
                role="ADM", site_ids=[SITE_1_ID, SITE_2_ID], is_active=True,
            ),
            User(
                id=NUT_ID, email="nutritionist@smallsf.com", name="Kim Nutrition",
                hashed_password=hash_password("nut1234"),
                role="NUT", site_ids=[SITE_1_ID], is_active=True,
            ),
            User(
                id=KIT_ID, email="kitchen@smallsf.com", name="Park Kitchen",
                hashed_password=hash_password("kit1234"),
                role="KIT", site_ids=[SITE_1_ID], is_active=True,
            ),
            User(
                id=QLT_ID, email="quality@smallsf.com", name="Lee Quality",
                hashed_password=hash_password("qlt1234"),
                role="QLT", site_ids=[SITE_1_ID, SITE_2_ID], is_active=True,
            ),
        ]
        db.add_all(users)
        await db.flush()

        # ── Nutrition Policy ──
        policy = NutritionPolicy(
            id=POLICY_1_ID,
            name="Standard Office Lunch",
            site_id=SITE_1_ID,
            criteria={
                "kcal": {"min": 600, "max": 900},
                "protein": {"min": 20},
                "sodium": {"max": 2000},
            },
            is_active=True,
        )
        db.add(policy)

        # ── Allergen Policy ──
        allergen_policy = AllergenPolicy(
            id=ALLERGEN_POLICY_1_ID,
            name="Standard 22 Allergens",
            site_id=SITE_1_ID,
            legal_allergens=[
                "난류", "우유", "메밀", "땅콩", "대두", "밀", "고등어", "게",
                "새우", "돼지고기", "복숭아", "토마토", "아황산류", "호두",
                "닭고기", "쇠고기", "오징어", "조개류", "잣", "쑥", "홍합", "전복",
            ],
            is_active=True,
        )
        db.add(allergen_policy)

        # ── Items (식재료) ──
        items = [
            Item(name="쌀", category="곡류", unit="kg", allergens=[], nutrition_per_100g={"kcal": 356, "protein": 6.8, "sodium": 1}),
            Item(name="닭가슴살", category="육류", unit="kg", allergens=["닭고기"], nutrition_per_100g={"kcal": 165, "protein": 31, "sodium": 74}),
            Item(name="두부", category="두류", unit="모", allergens=["대두"], nutrition_per_100g={"kcal": 76, "protein": 8, "sodium": 7}),
            Item(name="양파", category="채소", unit="kg", allergens=[], nutrition_per_100g={"kcal": 40, "protein": 1.1, "sodium": 4}),
            Item(name="계란", category="난류", unit="개", allergens=["난류"], nutrition_per_100g={"kcal": 155, "protein": 13, "sodium": 124}),
            Item(name="우유", category="유제품", unit="L", allergens=["우유"], nutrition_per_100g={"kcal": 61, "protein": 3.2, "sodium": 43}),
            Item(name="밀가루", category="곡류", unit="kg", allergens=["밀"], nutrition_per_100g={"kcal": 364, "protein": 10, "sodium": 2}),
            Item(name="돼지고기 목살", category="육류", unit="kg", allergens=["돼지고기"], nutrition_per_100g={"kcal": 242, "protein": 17, "sodium": 59}),
            Item(name="새우", category="해산물", unit="kg", allergens=["새우"], nutrition_per_100g={"kcal": 85, "protein": 20, "sodium": 566}),
            Item(name="시금치", category="채소", unit="kg", allergens=[], nutrition_per_100g={"kcal": 23, "protein": 2.9, "sodium": 79}),
        ]
        for item in items:
            item.is_active = True
        db.add_all(items)
        await db.flush()

        # ── Recipes ──
        recipes = [
            Recipe(
                name="닭가슴살 샐러드",
                category="양식", sub_category="샐러드",
                servings_base=1, prep_time_min=10, cook_time_min=15,
                difficulty="easy",
                ingredients=[
                    {"name": "닭가슴살", "amount": 150, "unit": "g"},
                    {"name": "양상추", "amount": 100, "unit": "g"},
                    {"name": "방울토마토", "amount": 50, "unit": "g"},
                    {"name": "올리브오일", "amount": 10, "unit": "ml"},
                ],
                steps=[
                    {"order": 1, "description": "닭가슴살을 소금, 후추로 밑간한다.", "duration_min": 5},
                    {"order": 2, "description": "팬에 올리브오일을 두르고 닭가슴살을 굽는다.", "duration_min": 10, "ccp": {"type": "temperature", "target": "75°C 이상", "critical": True}},
                    {"order": 3, "description": "채소를 씻고 적당한 크기로 자른다.", "duration_min": 5},
                    {"order": 4, "description": "구운 닭가슴살을 슬라이스하여 채소 위에 올린다."},
                ],
                nutrition_per_serving={"kcal": 220, "protein": 35, "fat": 8, "sodium": 380},
                allergens=["닭고기"],
                tags=["다이어트", "고단백", "샐러드"],
                created_by=NUT_ID,
            ),
            Recipe(
                name="된장찌개",
                category="한식", sub_category="탕/찌개",
                servings_base=4, prep_time_min=10, cook_time_min=20,
                difficulty="easy",
                ingredients=[
                    {"name": "된장", "amount": 60, "unit": "g"},
                    {"name": "두부", "amount": 200, "unit": "g"},
                    {"name": "양파", "amount": 100, "unit": "g"},
                    {"name": "호박", "amount": 80, "unit": "g"},
                    {"name": "대파", "amount": 30, "unit": "g"},
                    {"name": "고추", "amount": 10, "unit": "g"},
                    {"name": "다시마 육수", "amount": 800, "unit": "ml"},
                ],
                steps=[
                    {"order": 1, "description": "다시마 육수를 끓인다.", "duration_min": 5},
                    {"order": 2, "description": "된장을 풀어 넣고 두부, 양파, 호박을 넣는다.", "duration_min": 5},
                    {"order": 3, "description": "끓기 시작하면 대파, 고추를 넣고 5분 더 끓인다.", "duration_min": 10, "ccp": {"type": "temperature", "target": "100°C, 5분", "critical": True}},
                ],
                nutrition_per_serving={"kcal": 85, "protein": 6, "fat": 3, "sodium": 680},
                allergens=["대두"],
                tags=["한식", "국물", "사계절"],
                created_by=NUT_ID,
            ),
            Recipe(
                name="제육볶음",
                category="한식", sub_category="볶음",
                servings_base=4, prep_time_min=15, cook_time_min=15,
                difficulty="medium",
                ingredients=[
                    {"name": "돼지고기 목살", "amount": 400, "unit": "g"},
                    {"name": "양파", "amount": 150, "unit": "g"},
                    {"name": "고추장", "amount": 40, "unit": "g"},
                    {"name": "고춧가루", "amount": 10, "unit": "g"},
                    {"name": "간장", "amount": 20, "unit": "ml"},
                    {"name": "설탕", "amount": 15, "unit": "g"},
                    {"name": "마늘", "amount": 15, "unit": "g"},
                ],
                steps=[
                    {"order": 1, "description": "돼지고기를 한입 크기로 자르고 양념에 재운다.", "duration_min": 15},
                    {"order": 2, "description": "팬에 기름을 두르고 센 불에서 볶는다.", "duration_min": 10, "ccp": {"type": "temperature", "target": "75°C 이상", "critical": True}},
                    {"order": 3, "description": "양파를 넣고 함께 볶아 완성한다.", "duration_min": 5},
                ],
                nutrition_per_serving={"kcal": 310, "protein": 22, "fat": 18, "sodium": 720},
                allergens=["돼지고기", "대두", "밀"],
                tags=["한식", "매운맛", "인기"],
                created_by=NUT_ID,
            ),
        ]
        db.add_all(recipes)

        # ── Menu Plan (this week) ──
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)

        plan = MenuPlan(
            site_id=SITE_1_ID,
            title=f"Week {monday.isocalendar()[1]} Lunch Menu",
            period_start=monday,
            period_end=friday,
            status="confirmed",
            version=1,
            target_headcount=350,
            budget_per_meal=3500,
            nutrition_policy_id=POLICY_1_ID,
            allergen_policy_id=ALLERGEN_POLICY_1_ID,
            created_by=NUT_ID,
            confirmed_by=ADMIN_ID,
        )
        db.add(plan)
        await db.flush()

        # Menu items for Mon-Fri
        courses = ["rice", "soup", "main", "side1", "side2"]
        menu_items_data = [
            ("쌀밥", "된장찌개", "닭가슴살 샐러드", "시금치 나물", "김치"),
            ("쌀밥", "미역국", "제육볶음", "콩나물 무침", "김치"),
            ("쌀밥", "된장찌개", "고등어 구이", "도라지 무침", "김치"),
            ("쌀밥", "김치찌개", "닭가슴살 샐러드", "멸치볶음", "김치"),
            ("쌀밥", "시금치국", "제육볶음", "계란찜", "김치"),
        ]
        for day_offset, items_for_day in enumerate(menu_items_data):
            d = monday + timedelta(days=day_offset)
            for course_idx, item_name in enumerate(items_for_day):
                db.add(MenuPlanItem(
                    menu_plan_id=plan.id,
                    date=d,
                    meal_type="lunch",
                    course=courses[course_idx],
                    item_name=item_name,
                    nutrition={"kcal": 150 + day_offset * 10, "protein": 8 + course_idx * 2, "sodium": 200 + course_idx * 50},
                    allergens=[],
                    sort_order=course_idx,
                ))

        # ── HACCP Checklists (today) ──
        daily_template = [
            {"item": "식재료 입고 검수", "category": "receiving", "is_ccp": False},
            {"item": "냉장고 온도 확인 (0~5°C)", "category": "temperature", "is_ccp": True, "target": "0~5°C"},
            {"item": "냉동고 온도 확인 (-18°C 이하)", "category": "temperature", "is_ccp": True, "target": "-18°C 이하"},
            {"item": "조리 종사자 건강상태", "category": "personnel", "is_ccp": False},
            {"item": "가열 조리 중심온도 (75°C, 1분)", "category": "temperature", "is_ccp": True, "target": "75°C, 1분"},
        ]
        db.add(HaccpChecklist(
            site_id=SITE_1_ID,
            date=today,
            checklist_type="daily",
            meal_type="lunch",
            template=daily_template,
            status="pending",
        ))

        await db.commit()
        print("[seed] Seed data inserted successfully.")
        print(f"[seed] Admin login: admin@smallsf.com / admin1234")
        print(f"[seed] Nutritionist login: nutritionist@smallsf.com / nut1234")
        print(f"[seed] Kitchen login: kitchen@smallsf.com / kit1234")


if __name__ == "__main__":
    asyncio.run(seed())
