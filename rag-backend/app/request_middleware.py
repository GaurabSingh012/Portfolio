import hmac
import logging
import os
import re
import time
import uuid

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

logger = logging.getLogger("portfolio.request")


def install_request_middleware(app: FastAPI) -> None:
    """Add backend authentication and structured request logging."""

    @app.middleware("http")
    async def request_middleware(
        request: Request,
        call_next,
    ):
        incoming_id = request.headers.get("x-request-id", "").strip()

        # Accept only short, safe request IDs.
        if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", incoming_id):
            request_id = incoming_id
        else:
            request_id = uuid.uuid4().hex

        request.state.request_id = request_id
        started_at = time.perf_counter()

        try:
            # Protect the expensive chat endpoint.
            # Health checks and the root endpoint remain public.
            if request.url.path == "/chat" and request.method == "POST":
                expected_token = os.getenv("RAG_BACKEND_TOKEN")
                supplied_token = request.headers.get(
                    "x-rag-backend-token", ""
                )

                # Fail closed on Vercel if the secret was not configured.
                if os.getenv("VERCEL") == "1" and not expected_token:
                    response = JSONResponse(
                        status_code=503,
                        content={
                            "detail": "Chat backend authorization is not configured."
                        },
                    )

                elif expected_token and not hmac.compare_digest(
                    supplied_token,
                    expected_token,
                ):
                    response = JSONResponse(
                        status_code=401,
                        content={"detail": "Unauthorized."},
                    )

                else:
                    response = await call_next(request)

            else:
                response = await call_next(request)

        except Exception:
            logger.exception(
                "request_failed request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000

        response.headers["X-Request-ID"] = request_id

        # Do not log message contents, IP addresses, or credentials.
        logger.info(
            (
                "request_complete request_id=%s method=%s "
                "path=%s status_code=%s duration_ms=%.2f"
            ),
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response