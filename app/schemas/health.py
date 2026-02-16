from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class TaskDispatchResponse(BaseModel):
    status: str
    task_id: str
