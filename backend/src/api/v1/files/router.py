from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenException
from src.core.security import verify_file_link
from src.db.session import get_db
from src.providers.factory import get_storage_provider
from src.providers.storage_provider import StorageProvider
from src.services.file_service import FileService

router = APIRouter(tags=["files"])

_CONTENT_SECURITY_POLICY = "default-src 'none'; style-src 'unsafe-inline'; sandbox"


@router.get(
    "/files/{file_id}",
    response_class=Response,
    responses={
        200: {
            "description": "File content",
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def read_file(
    file_id: int,
    exp: Annotated[int, Query()],
    sig: Annotated[str, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> Response:
    if not verify_file_link(file_id, exp, sig, datetime.now(UTC)):
        raise ForbiddenException("Ссылка недействительна")

    file, data = await FileService(db, storage).read(file_id)

    disposition = "inline" if file.mime.startswith("image/") else "attachment"
    if disposition == "attachment" and file.original_name:
        disposition += f"; filename*=UTF-8''{quote(file.original_name)}"

    return Response(
        content=data,
        media_type=file.mime,
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Security-Policy": _CONTENT_SECURITY_POLICY,
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": disposition,
        },
    )
