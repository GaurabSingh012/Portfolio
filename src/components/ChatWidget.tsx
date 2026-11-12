
"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import styles from "./ChatWidget.module.css";

type Message = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

type ChatApiResponse = {
  answer?: unknown;
  error?: unknown;
  requestId?: unknown;
};

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function getFriendlyError(
  status: number,
  serverMessage?: string,
): string {
  switch (status) {
    case 400:
    case 422:
      return "I couldn't process that question. Please check it and try again.";

    case 401:
    case 403:
      return "The assistant is temporarily unavailable. Please try again later.";

    case 429:
      return "The assistant has reached its current request limit. Please wait a little and try again.";

    case 502:
      return "The assistant couldn't connect to its knowledge service. Please try again shortly.";

    case 503:
      return "The assistant is temporarily unavailable. Please try again later.";

    case 504:
      return "The assistant is taking too long to respond. Please try again.";

    default:
      return serverMessage ||
        "Something went wrong while processing your question. Please try again.";
  }
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! 👋 I'm Gaurab's portfolio assistant. Ask me about his projects, skills, education, or experience.",
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    }
  }, [messages, isOpen, isLoading, error]);

  async function sendQuestion(question: string) {
    if (!question || isLoading) {
      return;
    }

    setInput("");
    setError("");
    setIsLoading(true);

    setMessages((current) => [
      ...current,
      {
        id: createMessageId(),
        role: "user",
        content: question,
      },
    ]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
        signal: AbortSignal.timeout(70_000),
      });

      const payload = (await response
        .json()
        .catch(() => null)) as ChatApiResponse | null;

      if (!response.ok) {
        const serverMessage =
          typeof payload?.error === "string"
            ? payload.error
            : undefined;

        setError(getFriendlyError(response.status, serverMessage));

        // Preserve the question so the visitor can retry.
        setInput(question);
        return;
      }

      if (typeof payload?.answer !== "string") {
        throw new Error("The assistant returned an invalid response.");
      }

      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: payload.answer as string,
        },
      ]);
    } catch (caughtError) {
      console.warn("Portfolio chat request failed.");

      const isTimeout =
        caughtError instanceof Error &&
        (caughtError.name === "TimeoutError" ||
          caughtError.name === "AbortError");

      setError(
        isTimeout
          ? "The request took too long. Please try again."
          : "Could not reach the assistant. Check your connection and try again.",
      );

      // Preserve the visitor's original question.
      setInput(question);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const question = input.trim();

    if (!question || isLoading) {
      return;
    }

    await sendQuestion(question);
  }

  return (
    <>
      <button
        type="button"
        className={`${styles.launcher} ${
          isOpen ? styles.launcherOpen : ""
        }`}
        onClick={() => setIsOpen((open) => !open)}
        aria-label={isOpen ? "Close chat" : "Open portfolio assistant"}
        aria-expanded={isOpen}
        aria-controls="portfolio-chat-panel"
        title="Chat with my AI assistant"
      >
        {isOpen ? (
          "×"
        ) : (
          <Image
            src="/bot_logo.png"
            alt=""
            width={64}
            height={64}
            priority
            className={styles.launcherImage}
          />
        )}
      </button>

      {isOpen && (
        <section
          id="portfolio-chat-panel"
          className={styles.panel}
          role="dialog"
          aria-label="Portfolio AI assistant"
        >
          <header className={styles.header}>
            <div className={styles.avatar}>
              <Image
                src="/bot_logo.png"
                alt="Portfolio assistant robot"
                width={44}
                height={44}
                className={styles.avatarImage}
              />
            </div>

            <div className={styles.headerText}>
              <h2>Portfolio Assistant</h2>
              <p>
                <span className={styles.statusDot} />
                Ask about Gaurab&apos;s work
              </p>
            </div>

            <button
              type="button"
              className={styles.closeButton}
              onClick={() => setIsOpen(false)}
              aria-label="Close assistant"
            >
              ×
            </button>
          </header>

          <div className={styles.conversation} aria-live="polite">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`${styles.message} ${
                  message.role === "user"
                    ? styles.userMessage
                    : styles.assistantMessage
                }`}
              >
                <div
                  className={`${styles.bubble} ${
                    message.role === "user"
                      ? styles.userBubble
                      : styles.assistantBubble
                  }`}
                >
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
              </article>
            ))}

            {isLoading && (
              <div
                className={`${styles.message} ${styles.assistantMessage}`}
              >
                <div className={`${styles.bubble} ${styles.assistantBubble}`}>
                  Thinking...
                </div>
              </div>
            )}

            {error && (
              <p className={styles.error} role="alert">
                {error}
                <br />
                Your question is still in the input. You can try again.
              </p>
            )}

            <div ref={messagesEndRef} />
          </div>

          <form className={styles.form} onSubmit={handleSubmit}>
            <label
              htmlFor="portfolio-chat-input"
              className={styles.srOnly}
            >
              Ask a question about the portfolio
            </label>

            <input
              id="portfolio-chat-input"
              type="text"
              value={input}
              onChange={(event) => {
                setInput(event.target.value);
                if (error) setError("");
              }}
              placeholder="Ask me anything..."
              maxLength={1000}
              autoComplete="off"
              disabled={isLoading}
            />

            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
            >
              ↑
            </button>
          </form>

          <p className={styles.disclaimer}>
            AI-powered · Answers based on portfolio knowledge
          </p>
        </section>
      )}
    </>
  );
}
