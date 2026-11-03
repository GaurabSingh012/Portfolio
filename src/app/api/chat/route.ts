
import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

type BackendResponse = {
  answer?: unknown;
  sources?: unknown;
  detail?: unknown;
};

function errorResponse(
  message: string,
  status: number,
  requestId: string,
) {
  return NextResponse.json(
    { error: message, requestId },
    {
      status,
      headers: { "X-Request-ID": requestId },
    },
  );
}

export async function POST(request: NextRequest) {
  const requestId = randomUUID();

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return errorResponse(
      "Please send a valid JSON request.",
      400,
      requestId,
    );
  }

  if (
    typeof body !== "object" ||
    body === null ||
    !("question" in body) ||
    typeof body.question !== "string"
  ) {
    return errorResponse(
      "A question is required.",
      400,
      requestId,
    );
  }

  const question = body.question.trim();

  if (!question || question.length > 1000) {
    return errorResponse(
      "The question must contain 1–1000 characters.",
      400,
      requestId,
    );
  }

  const backendUrl = (
    process.env.RAG_BACKEND_URL ??
    (process.env.NODE_ENV === "development"
      ? "http://127.0.0.1:8000"
      : "")
  ).replace(/\/+$/, "");

  const backendToken = process.env.RAG_BACKEND_TOKEN;

  if (!backendUrl || (
    process.env.NODE_ENV === "production" && !backendToken
  )) {
    console.error(
      "Chat configuration missing. request_id=%s",
      requestId,
    );

    return errorResponse(
      "The assistant is temporarily unavailable. Please try again later.",
      503,
      requestId,
    );
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Request-ID": requestId,
  };

  if (backendToken) {
    headers["X-RAG-Backend-Token"] = backendToken;
  }

  try {
    const upstream = await fetch(`${backendUrl}/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({ question }),
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });

    const result = (await upstream
      .json()
      .catch(() => null)) as BackendResponse | null;

    if (!upstream.ok) {
      // Never expose internal authentication or infrastructure details.
      if (upstream.status === 401 || upstream.status === 403) {
        console.error(
          "Backend authentication failed. request_id=%s",
          requestId,
        );

        return errorResponse(
          "The assistant is temporarily unavailable. Please try again later.",
          502,
          requestId,
        );
      }

      const message =
        upstream.status === 429
          ? "The assistant has reached its current request limit. Please try again later."
          : typeof result?.detail === "string"
            ? result.detail
            : "The assistant couldn't answer right now.";

      console.warn(
        "Backend returned an error. request_id=%s status=%s",
        requestId,
        upstream.status,
      );

      return errorResponse(
        message,
        upstream.status === 429 ? 429 : 502,
        requestId,
      );
    }

    if (typeof result?.answer !== "string") {
      console.error(
        "Invalid backend response. request_id=%s",
        requestId,
      );

      return errorResponse(
        "The assistant returned an invalid response. Please try again.",
        502,
        requestId,
      );
    }

    return NextResponse.json(
      {
        answer: result.answer,
        sources: Array.isArray(result.sources)
          ? result.sources
          : [],
        requestId,
      },
      {
        headers: { "X-Request-ID": requestId },
      },
    );
  } catch (error) {
    const isTimeout =
      error instanceof Error && error.name === "TimeoutError";

    console.error(
      "Chat backend request failed. request_id=%s error=%s",
      requestId,
      error instanceof Error ? error.message : "Unknown error",
    );

    return errorResponse(
      isTimeout
        ? "The assistant is taking too long to respond. Please try again."
        : "Could not reach the AI assistant. Please try again shortly.",
      isTimeout ? 504 : 502,
      requestId,
    );
  }
}
