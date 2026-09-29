"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, Card, Empty, ErrorState, Field, Spinner, useAsync } from "@/components/ui";
import { api, unwrap } from "@/lib/api";

export default function DoctorPatients() {
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const list = useAsync(
    async () =>
      unwrap(await api.GET("/api/patients", { params: { query: { q: term || undefined, size: 50 } } })),
    [term],
  );
  return (
    <>
      <h1 className="text-2xl font-bold">My patients</h1>
      <Card>
        <form
          className="flex items-end gap-2"
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            setTerm(q);
          }}
        >
          <Field
            label="Search by name or phone"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="flex-1"
          />
          <Button type="submit">Search</Button>
        </form>
        {list.loading ? (
          <Spinner />
        ) : list.error ? (
          <ErrorState error={list.error} retry={list.reload} />
        ) : (list.data?.items.length ?? 0) === 0 ? (
          <Empty>No patients yet. Patients appear here once they have an appointment with you.</Empty>
        ) : (
          <ul className="mt-3 divide-y text-sm">
            {list.data?.items.map((p) => (
              <li key={p.id} className="flex items-center justify-between py-2">
                <span>
                  {p.first_name} {p.last_name} · {p.date_of_birth}
                </span>
                <Link className="text-blue-800 underline" href={`/doctor/patients/${p.id}`}>
                  Open chart
                  <span className="sr-only">
                    {" "}
                    for {p.first_name} {p.last_name}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
