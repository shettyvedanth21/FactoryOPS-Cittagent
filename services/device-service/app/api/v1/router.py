"""API version 1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.devices import router as devices_router

api_router = APIRouter()

api_router.include_router(devices_router, prefix="/devices", tags=["devices"])
