
import { NextResponse } from "next/server";

export const runtime = "nodejs";

const RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 5;

type RateLimitEntry = {
  count: number;
  resetAt: number;
};

// Best-effort per-process protection. Before public launch, use a shared
// rate limiter if you need consistent limits across serverless instances.
const rateLimitStore = new Map<string, RateLimitEntry>();

function isRateLimited(request: Request): boolean {
  const forwardedFor = request.headers
    .get("x-forwarded-for")
    ?.split(",")[0]
    ?.trim();

  const clientIp =
    forwardedFor ||
    request.headers.get("x-real-ip") ||
    "unknown";

  const now = Date.now();
  const existing = rateLimitStore.get(clientIp);

  if (!existing || existing.resetAt <= now) {
    rateLimitStore.set(clientIp, {
      count: 1,
      resetAt: now + RATE_LIMIT_WINDOW_MS,
    });
    return false;
  }

  if (existing.count >= MAX_REQUESTS_PER_WINDOW) {
    return true;
  }

  existing.count += 1;

  if (rateLimitStore.size > 1000) {
    for (const [key, entry] of rateLimitStore.entries()) {
      if (entry.resetAt <= now) {
        rateLimitStore.delete(key);
      }
    }
  }

  return false;
}

function escapeHtml(value: string): string {
  const characters: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };

  return value.replace(/[&<>"']/g, (character) => characters[character]);
}

function stringField(
  payload: Record<string, unknown>,
  field: string,
): string {
  return typeof payload[field] === "string"
    ? payload[field].trim()
    : "";
}

export async function POST(request: Request) {
  const contentLength = Number(
    request.headers.get("content-length") ?? "0",
  );

  if (Number.isFinite(contentLength) && contentLength > 15_000) {
    return NextResponse.json(
      { error: "Your message is too large." },
      { status: 413 },
    );
  }

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Please submit a valid form." },
      { status: 400 },
    );
  }

  if (
    typeof body !== "object" ||
    body === null ||
    Array.isArray(body)
  ) {
    return NextResponse.json(
      { error: "Please submit a valid form." },
      { status: 400 },
    );
  }

  const payload = body as Record<string, unknown>;

  // Quietly accept bot submissions that fill in the hidden honeypot field.
  if (stringField(payload, "website")) {
    return NextResponse.json({
      message: "Your message has been received.",
    });
  }

  const name = stringField(payload, "name");
  const email = stringField(payload, "email");
  const subject = stringField(payload, "subject")
    .replace(/[\r\n]+/g, " ")
    .slice(0, 150);
  const message = stringField(payload, "message");

  if (
    name.length < 2 ||
    name.length > 100 ||
    email.length > 254 ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ||
    message.length < 10 ||
    message.length > 5000
  ) {
    return NextResponse.json(
      {
        error:
          "Please check your name, email address, and message. The message must be between 10 and 5,000 characters.",
      },
      { status: 400 },
    );
  }

  const apiKey = process.env.RESEND_API_KEY;
  const recipient = process.env.CONTACT_TO_EMAIL;
  const sender = process.env.CONTACT_FROM_EMAIL;

  if (!apiKey || !recipient || !sender) {
    return NextResponse.json(
      {
        error:
          "The contact service has not been configured yet. Please email gaurabkus781@gmail.com directly for now.",
      },
      { status: 503 },
    );
  }

  if (isRateLimited(request)) {
    return NextResponse.json(
      {
        error:
          "Too many messages have been submitted. Please try again in a few minutes.",
      },
      { status: 429 },
    );
  }

  const safeName = escapeHtml(name);
  const safeEmail = escapeHtml(email);
  const safeMessage = escapeHtml(message).replace(/\r?\n/g, "<br>");

  const emailSubject =
    subject || `New portfolio message from ${name}`;

  try {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: sender,
        to: [recipient],
        reply_to: email,
        subject: emailSubject,
        text: [
          `Name: ${name}`,
          `Email: ${email}`,
          `Subject: ${emailSubject}`,
          "",
          message,
        ].join("\n"),
        html: `
          <h2>New portfolio enquiry</h2>
          <p><strong>Name:</strong> ${safeName}</p>
          <p><strong>Email:</strong> ${safeEmail}</p>
          <p><strong>Subject:</strong> ${escapeHtml(emailSubject)}</p>
          <hr />
          <p>${safeMessage}</p>
        `,
      }),
      cache: "no-store",
    });

    if (!response.ok) {
      const details = await response.text();

      console.error(
        "Resend email request failed:",
        response.status,
        details,
      );

      return NextResponse.json(
        {
          error:
            "Your message could not be sent right now. Please try again later.",
        },
        { status: 502 },
      );
    }

    return NextResponse.json({
      message: "Your message has been sent successfully. Thank you!",
    });
  } catch (error) {
    console.error("Contact email request failed:", error);

    return NextResponse.json(
      {
        error:
          "The email service could not be reached. Please try again later.",
      },
      { status: 502 },
    );
  }
}
