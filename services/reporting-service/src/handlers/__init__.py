from src.handlers.energy_reports import router as energy_router
from src.handlers.comparison_reports import router as comparison_router
from src.handlers.tariffs import router as tariffs_router
from src.handlers.report_common import router as common_router

__all__ = [
    "energy_router",
    "comparison_router",
    "tariffs_router",
    "common_router",
]
