from pydantic import AfterValidator, BaseModel

from src.core.texts import TEXT_INVALID_CHARACTER


def _reject_nul(value: str) -> str:
    if "\x00" in value:
        raise ValueError(TEXT_INVALID_CHARACTER)
    return value


NoNul = AfterValidator(_reject_nul)


class PaginatedResponse[T](BaseModel):
    total: int
    items: list[T]
