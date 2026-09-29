"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Alert, Button, Card, ErrorState, Field, Spinner, useAsync } from "@/components/ui";
import { API_URL, api, download, unwrap } from "@/lib/api";
import { addDays, todayLocal } from "@/lib/time";

type Summary = {
  appointments: {
    totals: Record<string, number>;
    per_day: {
      date: string;
      total: number;
      completed: number;
      no_show: number;
      cancelled: number;
      booked: number;
    }[];
  };
  no_show_rate: number;
  avg_booking_lead_hours: number | null;
  department_load: { department: string; appointments: number }[];
  ai_usage: {
    conversations: Record<string, number>;
    llm_replies: number;
    rule_based_emergency_responses: number;
    degraded_responses: number;
    avg_latency_ms: number | null;
    input_tokens: number;
    output_tokens: number;
  };
};

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-300 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-600">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}

export default function AdminDashboard() {
  const [from, setFrom] = useState(addDays(todayLocal(), -29));
  const [to, setTo] = useState(todayLocal());
  const [err, setErr] = useState<string | null>(null);
  const s = useAsync(
    async () =>
      unwrap(
        await api.GET("/api/admin/analytics/summary", { params: { query: { from, to } } }),
      ) as unknown as Summary,
    [from, to],
  );
  const d = s.data;
  return (
    <>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <Field
            label="From"
            type="date"
            value={from}
            onChange={(e) => e.target.value && setFrom(e.target.value)}
          />
          <Field
            label="To"
            type="date"
            value={to}
            onChange={(e) => e.target.value && setTo(e.target.value)}
          />
          <Button
            variant="secondary"
            onClick={() =>
              download(
                `/api/admin/analytics/export.csv?from=${from}&to=${to}`,
                `analytics_${from}_${to}.csv`,
              ).catch((e) => setErr(e.message))
            }
          >
            Export CSV
          </Button>
        </div>
        {err && (
          <div className="mt-2">
            <Alert kind="error">{err}</Alert>
          </div>
        )}
      </Card>
      {s.loading ? (
        <Spinner />
      ) : s.error || !d ? (
        <ErrorState error={s.error} retry={s.reload} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Appointments" value={d.appointments.totals.total} />
            <Kpi label="No-show rate" value={`${(d.no_show_rate * 100).toFixed(1)}%`} />
            <Kpi
              label="Avg booking lead time"
              value={d.avg_booking_lead_hours === null ? "—" : `${d.avg_booking_lead_hours} h`}
            />
            <Kpi
              label="AI assistant conversations"
              value={Object.values(d.ai_usage.conversations).reduce((a, b) => a + b, 0)}
            />
          </div>
          <Card title="Appointments per day">
            <div className="h-64" role="img" aria-label="Line chart of appointments per day">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={d.appointments.per_day}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="total"
                    name="Total"
                    stroke="#1d4ed8"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="no_show"
                    name="No-show"
                    stroke="#b91c1c"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer">View as table</summary>
              <table className="mt-2 w-full text-left">
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Total</th>
                    <th scope="col">No-show</th>
                  </tr>
                </thead>
                <tbody>
                  {d.appointments.per_day
                    .filter((r) => r.total > 0)
                    .map((r) => (
                      <tr key={r.date}>
                        <td>{r.date}</td>
                        <td>{r.total}</td>
                        <td>{r.no_show}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </details>
          </Card>
          <div className="grid gap-4 md:grid-cols-2">
            <Card title="Department load">
              <div className="h-64" role="img" aria-label="Bar chart of appointments by department">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={d.department_load} layout="vertical" margin={{ left: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis type="category" dataKey="department" width={110} />
                    <Tooltip />
                    <Bar dataKey="appointments" name="Appointments" fill="#1d4ed8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="AI assistant usage">
              <dl className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(d.ai_usage.conversations).map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-slate-600">{k} conversations</dt>
                    <dd className="font-semibold">{v}</dd>
                  </div>
                ))}
                <div>
                  <dt className="text-slate-600">LLM replies</dt>
                  <dd className="font-semibold">{d.ai_usage.llm_replies}</dd>
                </div>
                <div>
                  <dt className="text-slate-600">Rule-based emergency responses</dt>
                  <dd className="font-semibold">{d.ai_usage.rule_based_emergency_responses}</dd>
                </div>
                <div>
                  <dt className="text-slate-600">Degraded (AI down) responses</dt>
                  <dd className="font-semibold">{d.ai_usage.degraded_responses}</dd>
                </div>
                <div>
                  <dt className="text-slate-600">Avg latency</dt>
                  <dd className="font-semibold">{d.ai_usage.avg_latency_ms ?? "—"} ms</dd>
                </div>
                <div>
                  <dt className="text-slate-600">Tokens in / out</dt>
                  <dd className="font-semibold">
                    {d.ai_usage.input_tokens} / {d.ai_usage.output_tokens}
                  </dd>
                </div>
              </dl>
            </Card>
          </div>
        </>
      )}
      <p className="text-xs text-slate-600">API: {API_URL}</p>
    </>
  );
}
