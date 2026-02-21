"""API version 1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.rules import router as rules_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.alerts import router as alerts_router

api_router = APIRouter()

api_router.include_router(rules_router, prefix="/rules", tags=["rules"])
api_router.include_router(evaluation_router, prefix="/rules", tags=["evaluation"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
