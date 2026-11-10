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
      className="h-80 space-y-3 overflow-y-auto rounded-md border border-line bg-paper p-4"
    >
      {messages.length === 0 && <p className="text-sm text-slate-600">Type a message below to begin.</p>}
      {messages.map((m, i) => (
        <div key={i} className={cx("flex", m.role === "user" ? "justify-end" : "justify-start")}>
          <p
            className={cx(
              "max-w-[85%] whitespace-pre-wrap px-3.5 py-2.5 text-sm leading-relaxed",
              m.role === "user"
                ? "rounded-2xl rounded-br-md bg-navy-800 text-white"
                : "rounded-2xl rounded-bl-md border border-line bg-white text-navy-950",
            )}
          >
            <span className="sr-only">{m.role === "user" ? "You: " : "Assistant: "}</span>
            {m.text}
          </p>
        </div>
      ))}
      {busy && (
        <p className="flex items-center gap-2 text-xs text-slate-600">
          <span aria-hidden="true" className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-navy-400" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-navy-400 [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-navy-400 [animation-delay:300ms]" />
          </span>
          Assistant is typing…
        </p>
      )}
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
        className="min-w-0 flex-1 rounded-[5px] border border-slate-400 bg-white px-3 py-2.5 text-sm placeholder:text-slate-500 hover:border-navy-400 focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-100 disabled:bg-paper"
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded-[5px] bg-navy-800 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-navy-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-600 focus-visible:ring-offset-2 disabled:bg-navy-200 disabled:text-navy-600"
      >
        Send
      </button>
    </form>
  );
}
