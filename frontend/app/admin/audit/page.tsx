"use client";

import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorState, Field, Select, Spinner, useAsync } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { fmtDateTime } from "@/lib/time";

type Row = {
  id: number;
  created_at: string;
  user_id: string | null;
  role: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  method: string;
  path: string;
  status_code: number;
  ip: string | null;
};
type Page = { items: Row[]; total: number; page: number; size: number };

export default function AuditLogs() {
  const [f, setF] = useState({ resource_type: "", action: "", from: "", to: "" });
  const [applied, setApplied] = useState(f);
  const [page, setPage] = useState(1);
  const logs = useAsync(
    async () =>
      unwrap(
        await api.GET("/api/admin/audit-logs", {
          params: {
            query: {
              resource_type: applied.resource_type || undefined,
              action: applied.action || undefined,
              from: applied.from || undefined,
              to: applied.to || undefined,
              page,
              size: 50,
            },
          },
        }),
      ) as unknown as Page,
    [applied, page],
  );
  const pages = logs.data ? Math.max(1, Math.ceil(logs.data.total / logs.data.size)) : 1;
  return (
    <>
      <h1 className="text-2xl font-bold">Audit logs</h1>
      <Card>
        <form
          className="grid gap-3 md:grid-cols-5"
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setApplied(f);
          }}
        >
          <Field
            label="Resource"
            placeholder="patients, patients/visits…"
            value={f.resource_type}
            onChange={(e) => setF({ ...f, resource_type: e.target.value })}
          />
          <Select label="Action" value={f.action} onChange={(e) => setF({ ...f, action: e.target.value })}>
            <option value="">Any</option>
            {["read", "create", "update", "delete", "auth"].map((a) => (
              <option key={a}>{a}</option>
            ))}
          </Select>
          <Field
            label="From"
            type="date"
            value={f.from}
            onChange={(e) => setF({ ...f, from: e.target.value })}
          />
          <Field label="To" type="date" value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })} />
          <div className="flex items-end">
            <Button type="submit">Apply filters</Button>
          </div>
        </form>
      </Card>
      <Card>
        {logs.loading ? (
          <Spinner />
        ) : logs.error || !logs.data ? (
          <ErrorState error={logs.error} retry={logs.reload} />
        ) : logs.data.items.length === 0 ? (
          <Empty>No matching entries.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <caption className="sr-only">Audit log entries</caption>
              <thead>
                <tr className="text-left text-slate-700">
                  <th scope="col">Time</th>
                  <th scope="col">Role</th>
                  <th scope="col">Action</th>
                  <th scope="col">Resource</th>
                  <th scope="col">Status</th>
                  <th scope="col">IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.data.items.map((r) => (
                  <tr key={r.id} className="border-t">
                    <td className="py-1.5">{fmtDateTime(r.created_at)}</td>
                    <td>{r.role ?? "anon"}</td>
                    <td>{r.action}</td>
                    <td>
                      {r.resource_type}
                      {r.resource_id ? ` / ${r.resource_id.slice(0, 8)}…` : ""}
                    </td>
                    <td>
                      <Badge tone={r.status_code >= 400 ? "red" : "green"}>{r.status_code}</Badge>
                    </td>
                    <td>{r.ip}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <nav aria-label="Pagination" className="mt-3 flex items-center gap-2 text-sm">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <span>
            Page {page} of {pages} ({logs.data?.total ?? 0} entries)
          </span>
          <Button variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            Next
          </Button>
        </nav>
      </Card>
    </>
  );
}
