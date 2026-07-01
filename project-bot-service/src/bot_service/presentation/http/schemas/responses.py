from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exceptionName: str
    exceptionMessage: str
    stacktrace: list[str] = Field(default_factory=list)
