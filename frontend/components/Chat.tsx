"use client";

import { useEffect, useRef } from "react";
import { cx } from "./ui";

export type ChatMsg = { role: "user" | "assistant"; text: string };

export function ChatLog({ messages, busy }: { messages: ChatMsg[]; busy: boolean }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [messages, busy]);
  return (
    <div
      role="log"
      aria-live="polite"
      aria-label="Conversation"
      className="h-80 space-y-2 overflow-y-auto rounded border border-slate-300 bg-slate-50 p-3"
    >
      {messages.length === 0 && <p className="text-sm text-slate-600">Type a message to begin.</p>}
      {messages.map((m, i) => (
        <div key={i} className={cx("flex", m.role === "user" ? "justify-end" : "justify-start")}>
          <p
            className={cx(
              "max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm",
              m.role === "user"
                ? "bg-blue-700 text-white"
                : "border border-slate-300 bg-white text-slate-900",
            )}
          >
            <span className="sr-only">{m.role === "user" ? "You: " : "Assistant: "}</span>
            {m.text}
          </p>
        </div>
      ))}
      {busy && <p className="text-xs text-slate-600">Assistant is typing…</p>}
      <div ref={end} />
    </div>
  );
}

export function ChatInput({
  onSend,
  disabled,
  label = "Your message",
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
  label?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const v = ref.current?.value.trim();
        if (!v) return;
        onSend(v);
        if (ref.current) ref.current.value = "";
      }}
    >
      <label htmlFor="chat-input" className="sr-only">
        {label}
      </label>
      <input
        id="chat-input"
        ref={ref}
        maxLength={2000}
        disabled={disabled}
        autoComplete="off"
        placeholder={label}
        className="flex-1 rounded border border-slate-500 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:bg-slate-100"
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:bg-blue-300"
      >
        Send
      </button>
    </form>
  );
}
