"use client";

import { useState } from "react";
import { Alert, Badge, Button, Card, ErrorState, Field, Select, Spinner, useAsync } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";

function Departments({
  list,
  reload,
}: {
  list: { id: number; name: string; description?: string | null }[];
  reload: () => void;
}) {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  return (
    <Card title="Departments">
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <ul className="mb-3 divide-y text-sm">
        {list.map((d) => (
          <li key={d.id} className="py-1.5">
            <strong>{d.name}</strong>
            {d.description ? ` · ${d.description}` : ""}
          </li>
        ))}
      </ul>
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          const res = await api.POST("/api/admin/departments", { body: { name, description: desc || null } });
          if (res.data) {
            setMsg({ kind: "success", text: `Added ${res.data.name}.` });
            setName("");
            setDesc("");
            reload();
          } else setMsg({ kind: "error", text: errorMessage(res.error) });
        }}
      >
        <Field
          label="New department"
          required
          minLength={2}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Field label="Description" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <Button type="submit">Add department</Button>
      </form>
    </Card>
  );
}

export default function AdminUsers() {
  const users = useAsync(async () => unwrap(await api.GET("/api/admin/users")), []);
  const depts = useAsync(async () => unwrap(await api.GET("/api/departments")), []);
  const [f, setF] = useState({
    email: "",
    full_name: "",
    password: "",
    role: "staff",
    department_id: "",
    specialization: "",
  });
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setF({ ...f, [k]: e.target.value });

  return (
    <>
      <h1 className="page-title">Users</h1>
      <Card title="Create staff, doctor or admin account">
        <form
          className="grid gap-3 md:grid-cols-3"
          onSubmit={async (e) => {
            e.preventDefault();
            const res = await api.POST("/api/admin/users", {
              body: {
                email: f.email,
                full_name: f.full_name,
                password: f.password,
                role: f.role,
                department_id: f.role === "doctor" ? Number(f.department_id) : null,
                specialization: f.role === "doctor" ? f.specialization || null : null,
              },
            });
            if (res.data) {
              setMsg({ kind: "success", text: `Created ${res.data.email}.` });
              users.reload();
              setF({ ...f, email: "", full_name: "", password: "" });
            } else setMsg({ kind: "error", text: errorMessage(res.error) });
          }}
        >
          <div className="md:col-span-3">{msg && <Alert kind={msg.kind}>{msg.text}</Alert>}</div>
          <Field label="Full name" required value={f.full_name} onChange={set("full_name")} />
          <Field label="Email" type="email" required value={f.email} onChange={set("email")} />
          <Field
            label="Temporary password"
            type="password"
            required
            minLength={12}
            value={f.password}
            onChange={set("password")}
            autoComplete="new-password"
            hint="At least 12 characters"
          />
          <Select label="Role" value={f.role} onChange={set("role")}>
            <option value="staff">Reception staff</option>
            <option value="doctor">Doctor</option>
            <option value="admin">Admin</option>
          </Select>
          {f.role === "doctor" && (
            <>
              <Select label="Department" required value={f.department_id} onChange={set("department_id")}>
                <option value="">Select…</option>
                {depts.data?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Select>
              <Field label="Specialization" value={f.specialization} onChange={set("specialization")} />
            </>
          )}
          <div className="md:col-span-3">
            <Button type="submit">Create user</Button>
          </div>
        </form>
      </Card>
      <Departments list={depts.data ?? []} reload={depts.reload} />
      <Card title="All users">
        {users.loading ? (
          <Spinner />
        ) : users.error ? (
          <ErrorState error={users.error} retry={users.reload} />
        ) : (
          <table className="w-full text-sm">
            <caption className="sr-only">User accounts</caption>
            <thead>
              <tr className="text-left text-slate-700">
                <th scope="col">Name</th>
                <th scope="col">Email</th>
                <th scope="col">Role</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {users.data?.map((u) => (
                <tr key={u.id} className="border-t">
                  <td className="py-2">{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>
                    <Badge tone="blue">{u.role}</Badge>
                  </td>
                  <td>
                    {u.is_active ? <Badge tone="green">active</Badge> : <Badge tone="red">disabled</Badge>}
                  </td>
                  <td className="text-right">
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        const res = await api.PATCH("/api/admin/users/{user_id}/active", {
                          params: { path: { user_id: u.id }, query: { active: !u.is_active } },
                        });
                        if (!res.data) setMsg({ kind: "error", text: errorMessage(res.error) });
                        else users.reload();
                      }}
                    >
                      {u.is_active ? "Deactivate" : "Activate"}
                      <span className="sr-only"> {u.email}</span>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}
