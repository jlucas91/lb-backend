from fastapi import APIRouter

from app.schemas.health import HealthResponse, TaskDispatchResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.post("/tasks/ping", response_model=TaskDispatchResponse)
async def dispatch_ping() -> TaskDispatchResponse:
    from app.tasks.example import ping

    result = ping.delay()
    return TaskDispatchResponse(status="dispatched", task_id=str(result.id))
