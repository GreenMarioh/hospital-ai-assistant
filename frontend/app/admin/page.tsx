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

/* Chart tokens: validated pair (light surface, CVD-separated); grid and ticks stay recessive. */
const SERIES_TOTAL = "#3A5BA0";
const SERIES_NO_SHOW = "#C2410C";
const GRID = "#DBE1EB";
const TICK = { fontSize: 12, fill: "#475569" };
const TOOLTIP = {
  contentStyle: { borderRadius: 6, border: "1px solid #DBE1EB", fontSize: 13, color: "#0F1F3D" },
  labelStyle: { fontWeight: 600, marginBottom: 4 },
};

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border-l-2 border-navy-200 py-1 pl-4">
      <p className="text-[13px] text-slate-600">{label}</p>
      <p className="num mt-1 font-serif text-[2rem] font-semibold leading-none text-navy-900">{value}</p>
    </div>
  );
}

export default function AdminDashboard() {
  const [from, setFrom] = useState(addDays(todayLocal(), -29));
  const [to, setTo] = useState(addDays(todayLocal(), 14)); // include upcoming bookings
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
      <h1 className="page-title">Dashboard</h1>
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
          <div className="grid grid-cols-2 gap-x-4 gap-y-6 rounded-lg border border-line bg-white p-5 md:grid-cols-4 md:p-6">
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
                  <CartesianGrid stroke={GRID} vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v: string) => v.slice(5)}
                    tick={TICK}
                    tickLine={false}
                    axisLine={{ stroke: GRID }}
                    minTickGap={16}
                  />
                  <YAxis allowDecimals={false} tick={TICK} tickLine={false} axisLine={false} width={32} />
                  <Tooltip {...TOOLTIP} />
                  <Legend iconType="plainline" wrapperStyle={{ fontSize: 13, color: "#475569" }} />
                  <Line
                    type="linear"
                    dataKey="total"
                    name="Total"
                    stroke={SERIES_TOTAL}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="linear"
                    dataKey="no_show"
                    name="No-show"
                    stroke={SERIES_NO_SHOW}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer text-navy-700 hover:text-navy-900">View as table</summary>
              <table className="data-table mt-3 w-full max-w-md text-left">
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
                  <BarChart data={d.department_load} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <CartesianGrid stroke={GRID} horizontal={false} />
                    <XAxis
                      type="number"
                      allowDecimals={false}
                      tick={TICK}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="department"
                      width={110}
                      tick={{ ...TICK, fill: "#16294F" }}
                      tickLine={false}
                      axisLine={{ stroke: GRID }}
                    />
                    <Tooltip {...TOOLTIP} cursor={{ fill: "#EEF2F8" }} />
                    <Bar
                      dataKey="appointments"
                      name="Appointments"
                      fill={SERIES_TOTAL}
                      maxBarSize={24}
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="AI assistant usage">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
                {Object.entries(d.ai_usage.conversations).map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-slate-600 first-letter:uppercase">{k} conversations</dt>
                    <dd className="num mt-0.5 font-semibold text-navy-900">{v}</dd>
                  </div>
                ))}
                <div>
                  <dt className="text-slate-600">LLM replies</dt>
                  <dd className="num mt-0.5 font-semibold text-navy-900">{d.ai_usage.llm_replies}</dd>
                </div>
                <div>
                  <dt className="text-slate-600">Rule-based emergency responses</dt>
                  <dd className="num mt-0.5 font-semibold text-navy-900">
                    {d.ai_usage.rule_based_emergency_responses}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-600">Degraded (AI down) responses</dt>
                  <dd className="num mt-0.5 font-semibold text-navy-900">{d.ai_usage.degraded_responses}</dd>
                </div>
                <div>
                  <dt className="text-slate-600">Avg latency</dt>
                  <dd className="num mt-0.5 font-semibold text-navy-900">
                    {d.ai_usage.avg_latency_ms ?? "—"} ms
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-600">Tokens in / out</dt>
                  <dd className="num mt-0.5 font-semibold text-navy-900">
                    {d.ai_usage.input_tokens} / {d.ai_usage.output_tokens}
                  </dd>
                </div>
              </dl>
            </Card>
          </div>
        </>
      )}
      <p className="text-xs text-slate-600">
        API: <span className="num">{API_URL}</span>
      </p>
    </>
  );
}
