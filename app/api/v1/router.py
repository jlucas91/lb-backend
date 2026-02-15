from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    files,
    health,
    locations,
    production_locations,
    production_members,
    productions,
    shares,
)

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(locations.router, prefix="/locations", tags=["locations"])
router.include_router(files.router, prefix="/locations", tags=["files"])
router.include_router(shares.router, prefix="/locations", tags=["shares"])
router.include_router(shares.shared_with_me_router, tags=["shares"])
router.include_router(productions.router, prefix="/productions", tags=["productions"])
router.include_router(
    production_members.router, prefix="/productions", tags=["production-members"]
)
router.include_router(
    production_locations.router,
    prefix="/productions",
    tags=["production-locations"],
)
