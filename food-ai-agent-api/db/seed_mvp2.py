"""Seed data for MVP 2 Purchase & Inventory — vendors, prices, initial inventory."""
import asyncio
import sys
import os
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.db.database import async_session_factory
from app.models.orm.purchase import Vendor, VendorPrice
from app.models.orm.inventory import Inventory
from app.models.orm.item import Item
from app.models.orm.site import Site


SAMPLE_VENDORS = [
    {
        "name": "한국청과",
        "business_no": "123-45-67890",
        "contact": {"phone": "02-1234-5678", "email": "order@hankook.com", "rep": "김청과"},
        "categories": ["채소", "과일"],
        "lead_days": 1,
        "rating": Decimal("4.5"),
        "notes": "당일 새벽배송 가능",
    },
    {
        "name": "서울수산",
        "business_no": "234-56-78901",
        "contact": {"phone": "02-2345-6789", "email": "fish@seoul.com", "rep": "박수산"},
        "categories": ["수산", "해산물"],
        "lead_days": 2,
        "rating": Decimal("4.3"),
        "notes": "신선도 보증 반품 정책 있음",
    },
    {
        "name": "우리축산",
        "business_no": "345-67-89012",
        "contact": {"phone": "031-345-6789", "email": "meat@woori.com", "rep": "이축산"},
        "categories": ["육류", "가공육"],
        "lead_days": 1,
        "rating": Decimal("4.7"),
        "notes": "HACCP 인증 업체",
    },
    {
        "name": "한라양념",
        "business_no": "456-78-90123",
        "contact": {"phone": "064-456-7890", "email": "sauce@halla.com", "rep": "고양념"},
        "categories": ["양념", "소스", "조미료"],
        "lead_days": 3,
        "rating": Decimal("4.1"),
        "notes": "대용량 주문 5% 할인",
    },
    {
        "name": "대한유가공",
        "business_no": "567-89-01234",
        "contact": {"phone": "02-5678-9012", "email": "dairy@daehan.com", "rep": "유가공"},
        "categories": ["유제품", "냉동"],
        "lead_days": 2,
        "rating": Decimal("4.4"),
        "notes": "냉장/냉동 온도 관리 차량 보유",
    },
]


async def seed():
    async with async_session_factory() as session:
        # Check if vendors already exist
        existing = (await session.execute(select(Vendor).limit(1))).scalar_one_or_none()
        if existing:
            print("Vendors already exist. Skipping vendor seed.")
        else:
            print("Seeding vendors...")
            vendors_created = []
            for vd in SAMPLE_VENDORS:
                vendor = Vendor(**vd, is_active=True)
                session.add(vendor)
                vendors_created.append(vendor)
            await session.flush()
            print(f"Created {len(vendors_created)} vendors.")

        # Load all vendors
        all_vendors = (await session.execute(select(Vendor).where(Vendor.is_active == True))).scalars().all()
        vendors_map = {v.name: v for v in all_vendors}

        # Load first 20 items for seeding prices
        items = (await session.execute(select(Item).where(Item.is_active == True).limit(20))).scalars().all()
        sites = (await session.execute(select(Site).where(Site.is_active == True).limit(3))).scalars().all()

        if not items:
            print("No items found. Skipping price seed.")
        else:
            # Check if prices exist
            existing_prices = (await session.execute(select(VendorPrice).limit(1))).scalar_one_or_none()
            if existing_prices:
                print("Vendor prices already exist. Skipping price seed.")
            else:
                print(f"Seeding vendor prices for {len(items)} items...")
                today = date.today()
                prices_created = 0

                # Category → vendor mapping
                category_vendor_map = {
                    "채소": ["한국청과"],
                    "과일": ["한국청과"],
                    "수산": ["서울수산"],
                    "해산물": ["서울수산"],
                    "육류": ["우리축산"],
                    "가공육": ["우리축산"],
                    "양념": ["한라양념"],
                    "소스": ["한라양념"],
                    "조미료": ["한라양념"],
                    "유제품": ["대한유가공"],
                    "냉동": ["대한유가공"],
                }

                # Default price ranges by category
                category_price_range = {
                    "채소": (800, 3000),
                    "과일": (2000, 8000),
                    "수산": (5000, 20000),
                    "해산물": (3000, 15000),
                    "육류": (8000, 25000),
                    "가공육": (5000, 15000),
                    "양념": (1000, 5000),
                    "소스": (2000, 8000),
                    "조미료": (500, 3000),
                    "유제품": (1500, 6000),
                    "냉동": (3000, 12000),
                }

                import random
                random.seed(42)

                for item in items:
                    cat = item.category
                    vendor_names = category_vendor_map.get(cat, ["한국청과"])
                    price_range = category_price_range.get(cat, (1000, 5000))

                    for vendor_name in vendor_names:
                        vendor = vendors_map.get(vendor_name)
                        if not vendor:
                            continue

                        base_price = random.randint(price_range[0], price_range[1])
                        vp = VendorPrice(
                            vendor_id=vendor.id,
                            item_id=item.id,
                            unit_price=Decimal(str(base_price)),
                            unit=item.unit,
                            currency="KRW",
                            effective_from=today,
                            is_current=True,
                            source="seed",
                        )
                        session.add(vp)
                        prices_created += 1

                        # Add a competing price from general vendor (한국청과 or 우리축산)
                        if vendor_name != "한국청과" and cat in ("채소", "양념"):
                            v2 = vendors_map.get("한국청과")
                            if v2:
                                alt_price = int(base_price * random.uniform(0.95, 1.15))
                                vp2 = VendorPrice(
                                    vendor_id=v2.id,
                                    item_id=item.id,
                                    unit_price=Decimal(str(alt_price)),
                                    unit=item.unit,
                                    currency="KRW",
                                    effective_from=today,
                                    is_current=True,
                                    source="seed",
                                )
                                session.add(vp2)
                                prices_created += 1

                await session.flush()
                print(f"Created {prices_created} vendor price records.")

        # Seed initial inventory
        if not sites or not items:
            print("No sites or items found. Skipping inventory seed.")
        else:
            existing_inv = (await session.execute(select(Inventory).limit(1))).scalar_one_or_none()
            if existing_inv:
                print("Inventory already exists. Skipping inventory seed.")
            else:
                print(f"Seeding inventory for {len(sites)} sites x {len(items)} items...")
                import random
                random.seed(123)
                inv_created = 0

                for site in sites:
                    for item in items[:10]:  # First 10 items per site
                        qty = random.uniform(5, 50)
                        inv = Inventory(
                            site_id=site.id,
                            item_id=item.id,
                            quantity=Decimal(str(round(qty, 3))),
                            unit=item.unit,
                            location="창고",
                            min_qty=Decimal(str(round(qty * 0.2, 3))),
                        )
                        session.add(inv)
                        inv_created += 1

                await session.flush()
                print(f"Created {inv_created} inventory records.")

        await session.commit()
        print("MVP 2 seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
