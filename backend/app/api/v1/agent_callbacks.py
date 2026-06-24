import logging

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response

from app.config import get_code_review_settings
from app.dependencies import get_conn
from app.schemas.review_callback import ReviewCallbackEvent
from app.services.review_callback_auth import verify_payload_signature
from app.services.review_callback_handler import handle_review_callback

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/review-events", status_code=status.HTTP_204_NO_CONTENT)
async def agent_review_events(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    x_review_signature_256: str | None = Header(None, alias="X-Review-Signature-256"),
) -> Response:
    body = await request.body()
    secret = get_code_review_settings().agent_callback_secret
    if not verify_payload_signature(body, x_review_signature_256, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid callback signature",
        )

    try:
        event = ReviewCallbackEvent.model_validate_json(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid callback payload",
        ) from exc

    try:
        await handle_review_callback(conn, event)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
