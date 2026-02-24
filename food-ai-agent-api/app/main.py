from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, chat, menu_plans, recipes, work_orders, haccp, dashboard, documents, sites, items, policies, users, audit_logs, vendors, boms, purchase_orders, inventory, forecast, waste, cost, claims


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url=f"{settings.api_v1_prefix}/docs",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    prefix = settings.api_v1_prefix
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(chat.router, prefix=f"{prefix}/chat", tags=["chat"])
    app.include_router(menu_plans.router, prefix=f"{prefix}/menu-plans", tags=["menu-plans"])
    app.include_router(recipes.router, prefix=f"{prefix}/recipes", tags=["recipes"])
    app.include_router(work_orders.router, prefix=f"{prefix}/work-orders", tags=["work-orders"])
    app.include_router(haccp.router, prefix=f"{prefix}/haccp", tags=["haccp"])
    app.include_router(dashboard.router, prefix=f"{prefix}/dashboard", tags=["dashboard"])
    app.include_router(documents.router, prefix=f"{prefix}/documents", tags=["documents"])
    app.include_router(sites.router, prefix=f"{prefix}/sites", tags=["sites"])
    app.include_router(items.router, prefix=f"{prefix}/items", tags=["items"])
    app.include_router(policies.router, prefix=f"{prefix}/policies", tags=["policies"])
    app.include_router(users.router, prefix=f"{prefix}/users", tags=["users"])
    app.include_router(audit_logs.router, prefix=f"{prefix}/audit-logs", tags=["audit-logs"])
    # MVP 2 — Purchase & Inventory
    app.include_router(vendors.router, prefix=f"{prefix}/vendors", tags=["vendors"])
    app.include_router(boms.router, prefix=f"{prefix}/boms", tags=["boms"])
    app.include_router(purchase_orders.router, prefix=f"{prefix}/purchase-orders", tags=["purchase-orders"])
    app.include_router(inventory.router, prefix=f"{prefix}/inventory", tags=["inventory"])
    # MVP 3 — Demand / Waste / Cost / Claims
    app.include_router(forecast.router, prefix=f"{prefix}/forecast", tags=["forecast"])
    app.include_router(waste.router, prefix=f"{prefix}/waste", tags=["waste"])
    app.include_router(cost.router, prefix=f"{prefix}/cost", tags=["cost"])
    app.include_router(claims.router, prefix=f"{prefix}/claims", tags=["claims"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
