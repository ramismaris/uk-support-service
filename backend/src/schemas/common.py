from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    total: int
    items: list[T]
