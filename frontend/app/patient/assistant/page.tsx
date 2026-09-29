"use client";

import Link from "next/link";
import { useState } from "react";
import { ChatInput, ChatLog, type ChatMsg } from "@/components/Chat";
import { AiDisclaimer, Alert, Badge, Button, Card, Field } from "@/components/ui";
import { api, errorMessage, type Schemas } from "@/lib/api";

type Triage = Schemas["TriageOut"];

function TriagePanel() {
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [conv, setConv] = useState<string | undefined>();
  const [last, setLast] = useState<Triage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(text: string) {
    setMsgs((m) => [...m, { role: "user", text }]);
    setBusy(true);
    setError(null);
    const res = await api.POST("/api/ai/triage/message", { body: { message: text, conversation_id: conv } });
    setBusy(false);
    if (!res.data) {
      setError(errorMessage(res.error));
      return;
    }
    setConv(res.data.conversation_id);
    setLast(res.data);
    setMsgs((m) => [...m, { role: "assistant", text: res.data!.reply }]);
  }

  function restart() {
    setMsgs([]);
    setConv(undefined);
    setLast(null);
  }

  return (
    <Card title="Symptom check">
      <div className="space-y-3">
        <AiDisclaimer />
        {last?.emergency && (
          <Alert kind="emergency">{last.emergency_banner} Call your local emergency number now.</Alert>
        )}
        {error && <Alert kind="error">{error}</Alert>}
        {last && !last.ai_available && (
          <Alert kind="warning">
            The assistant is unavailable right now. You can still{" "}
            <Link className="underline" href="/patient/book">
              book an appointment
            </Link>
            .
          </Alert>
        )}
        <ChatLog messages={msgs} busy={busy} />
        {last?.result && (
          <div className="rounded border border-slate-300 p-3 text-sm" aria-label="Triage result">
            <p>
              Urgency:{" "}
              <Badge
                tone={
                  last.result.urgency === "emergency"
                    ? "red"
                    : last.result.urgency === "urgent"
                      ? "amber"
                      : "green"
                }
              >
                {last.result.urgency}
              </Badge>{" "}
              · Suggested department: <strong>{last.result.department ?? "—"}</strong>
            </p>
            <p className="mt-1 text-slate-700">{last.result.rationale}</p>
            {!last.emergency && (
              <Link className="mt-2 inline-block font-medium text-blue-800 underline" href="/patient/book">
                Book an appointment
              </Link>
            )}
          </div>
        )}
        {last?.done ? (
          <Button variant="secondary" onClick={restart}>
            Start a new check
          </Button>
        ) : (
          <ChatInput onSend={send} disabled={busy} label="Describe your symptoms" />
        )}
      </div>
    </Card>
  );
}

function FaqPanel() {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState<Schemas["FaqOut"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  return (
    <Card title="Hospital FAQ">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          const res = await api.POST("/api/ai/faq", { body: { question: q } });
          setBusy(false);
          if (res.data) setOut(res.data);
          else setError(errorMessage(res.error));
        }}
      >
        <Field
          label="Ask about visiting hours, departments, policies…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          required
          minLength={2}
          maxLength={500}
        />
        <Button type="submit" disabled={busy}>
          {busy ? "Searching…" : "Ask"}
        </Button>
      </form>
      {error && (
        <div className="mt-3">
          <Alert kind="error">{error}</Alert>
        </div>
      )}
      {out && (
        <div className="mt-3 space-y-2 text-sm" aria-live="polite">
          <p className="whitespace-pre-wrap rounded border border-slate-300 bg-white p-3">{out.answer}</p>
          {out.sources.length > 0 && (
            <p className="text-xs text-slate-600">Source: {out.sources.map((s) => s.title).join(", ")}</p>
          )}
        </div>
      )}
    </Card>
  );
}

export default function AssistantPage() {
  return (
    <>
      <h1 className="text-2xl font-bold">Symptom check &amp; FAQ</h1>
      <TriagePanel />
      <FaqPanel />
    </>
  );
}
