"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Button, Card, Empty, ErrorState, Field, Spinner, useAsync } from "@/components/ui";
import { api, unwrap } from "@/lib/api";

const blank = {
  first_name: "",
  last_name: "",
  date_of_birth: "",
  phone: "",
  email: "",
  sex: "",
  blood_group: "",
  allergies: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  insurance_provider: "",
  insurance_id: "",
};

function Register({ onDone }: { onDone: () => void }) {
  const [f, setF] = useState(blank);
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const set = (k: keyof typeof blank) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: e.target.value });
  return (
    <Card title="Register a patient">
      <form
        className="grid gap-3 md:grid-cols-3"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            const p = unwrap(
              await api.POST("/api/patients", {
                body: {
                  first_name: f.first_name,
                  last_name: f.last_name,
                  date_of_birth: f.date_of_birth,
                  phone: f.phone || null,
                  email: f.email || null,
                  sex: f.sex || null,
                  blood_group: f.blood_group || null,
                  allergies: f.allergies
                    ? f.allergies
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean)
                    : [],
                  emergency_contact_name: f.emergency_contact_name || null,
                  emergency_contact_phone: f.emergency_contact_phone || null,
                  insurance_provider: f.insurance_provider || null,
                  insurance_id: f.insurance_id || null,
                },
              }),
            );
            setMsg({ kind: "success", text: `Registered ${p.first_name} ${p.last_name}.` });
            setF(blank);
            onDone();
          } catch (err) {
            setMsg({ kind: "error", text: (err as Error).message });
          }
        }}
      >
        <div className="md:col-span-3">{msg && <Alert kind={msg.kind}>{msg.text}</Alert>}</div>
        <Field label="First name" required value={f.first_name} onChange={set("first_name")} />
        <Field label="Last name" required value={f.last_name} onChange={set("last_name")} />
        <Field
          label="Date of birth"
          type="date"
          required
          value={f.date_of_birth}
          onChange={set("date_of_birth")}
        />
        <Field label="Phone" type="tel" value={f.phone} onChange={set("phone")} />
        <Field label="Email" type="email" value={f.email} onChange={set("email")} />
        <Field label="Sex" value={f.sex} onChange={set("sex")} />
        <Field
          label="Blood group"
          placeholder="A+"
          pattern="(A|B|AB|O)[+-]"
          value={f.blood_group}
          onChange={set("blood_group")}
        />
        <Field
          label="Allergies (comma separated)"
          value={f.allergies}
          onChange={set("allergies")}
          className="md:col-span-2"
        />
        <Field
          label="Emergency contact name"
          value={f.emergency_contact_name}
          onChange={set("emergency_contact_name")}
        />
        <Field
          label="Emergency contact phone"
          type="tel"
          value={f.emergency_contact_phone}
          onChange={set("emergency_contact_phone")}
        />
        <Field label="Insurance provider" value={f.insurance_provider} onChange={set("insurance_provider")} />
        <Field
          label="Insurance ID"
          value={f.insurance_id}
          onChange={set("insurance_id")}
          hint="Stored encrypted"
        />
        <div className="md:col-span-3">
          <Button type="submit">Register patient</Button>
        </div>
      </form>
    </Card>
  );
}

export default function ReceptionPatients() {
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const [page, setPage] = useState(1);
  const list = useAsync(
    async () =>
      unwrap(await api.GET("/api/patients", { params: { query: { q: term || undefined, page, size: 20 } } })),
    [term, page],
  );
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.size)) : 1;
  return (
    <>
      <h1 className="page-title">Patients</h1>
      <Card title="Search patients">
        <form
          className="flex flex-wrap items-end gap-2"
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setTerm(q);
          }}
        >
          <Field
            label="Name, phone or patient ID"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="min-w-64 flex-1"
          />
          <Button type="submit">Search</Button>
        </form>
        {list.loading ? (
          <Spinner />
        ) : list.error ? (
          <ErrorState error={list.error} retry={list.reload} />
        ) : (list.data?.items.length ?? 0) === 0 ? (
          <Empty>No patients found.</Empty>
        ) : (
          <>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Patient search results</caption>
                <thead>
                  <tr className="text-left text-slate-700">
                    <th scope="col" className="py-1">
                      Name
                    </th>
                    <th scope="col">DOB</th>
                    <th scope="col">Phone</th>
                    <th scope="col">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {list.data?.items.map((p) => (
                    <tr key={p.id} className="border-t">
                      <td className="py-2">
                        {p.first_name} {p.last_name}
                      </td>
                      <td className="whitespace-nowrap pr-3">{p.date_of_birth}</td>
                      <td className="whitespace-nowrap pr-3">{p.phone ?? "—"}</td>
                      <td className="text-right">
                        <Link className="link" href={`/reception/patients/${p.id}`}>
                          Open
                          <span className="sr-only">
                            {" "}
                            {p.first_name} {p.last_name}
                          </span>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <nav aria-label="Pagination" className="mt-3 flex items-center gap-2 text-sm">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Previous
              </Button>
              <span>
                Page {page} of {pages} ({list.data?.total} patients)
              </span>
              <Button variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
                Next
              </Button>
            </nav>
          </>
        )}
      </Card>
      <Register onDone={list.reload} />
    </>
  );
}
