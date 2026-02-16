from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    episodes,
    files,
    folders,
    health,
    location_files,
    locations,
    production_locations,
    production_members,
    productions,
    project_location_files,
    project_locations,
    project_members,
    projects,
    scoutings,
    scripted_locations,
    shares,
)

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(locations.router, prefix="/locations", tags=["locations"])
router.include_router(files.router, prefix="/files", tags=["files"])
router.include_router(
    location_files.router, prefix="/locations", tags=["location-files"]
)
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
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(
    project_members.router, prefix="/projects", tags=["project-members"]
)
router.include_router(
    project_locations.router, prefix="/projects", tags=["project-locations"]
)
router.include_router(
    project_location_files.router,
    prefix="/projects",
    tags=["project-location-files"],
)
router.include_router(episodes.router, prefix="/projects", tags=["episodes"])
router.include_router(folders.router, prefix="/projects", tags=["folders"])
router.include_router(
    scripted_locations.router, prefix="/projects", tags=["scripted-locations"]
)
router.include_router(scoutings.router, prefix="/locations", tags=["scoutings"])
