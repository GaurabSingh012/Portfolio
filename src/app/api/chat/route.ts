
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

type BackendResponse = {
  answer?: unknown;
  sources?: unknown;
  detail?: unknown;
};

export async function POST(request: NextRequest) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Please send a valid JSON request." },
      { status: 400 },
    );
  }

  if (
    typeof body !== "object" ||
    body === null ||
    !("question" in body) ||
    typeof body.question !== "string"
  ) {
    return NextResponse.json(
      { error: "A question is required." },
      { status: 400 },
    );
  }

  const question = body.question.trim();

  if (!question || question.length > 1000) {
    return NextResponse.json(
      { error: "The question must contain 1–1000 characters." },
      { status: 400 },
    );
  }

  const backendUrl = (
    process.env.RAG_BACKEND_URL ?? "http://127.0.0.1:8000"
  ).replace(/\/+$/, "");

  try {
    const upstream = await fetch(`${backendUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });

    const result = (await upstream.json().catch(() => null)) as
      | BackendResponse
      | null;

    if (!upstream.ok) {
      const message =
        typeof result?.detail === "string"
          ? result.detail
          : "The chat service could not answer right now.";

      return NextResponse.json(
        { error: message },
        { status: upstream.status },
      );
    }

    if (typeof result?.answer !== "string") {
      return NextResponse.json(
        { error: "The chat service returned an invalid response." },
        { status: 502 },
      );
    }

    return NextResponse.json({
      answer: result.answer,
      sources: Array.isArray(result.sources) ? result.sources : [],
    });
  } catch (error) {
    console.error("Chat backend request failed:", error);

    return NextResponse.json(
      {
        error:
          "Could not reach the AI assistant. Please try again shortly.",
      },
      { status: 502 },
    );
  }
}
