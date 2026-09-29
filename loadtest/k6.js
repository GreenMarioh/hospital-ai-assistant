// k6 run -e BASE_URL=http://backend:8000 loadtest/k6.js
// 50 concurrent virtual users on non-AI endpoints; target: p95 < 300 ms, errors < 1 %.
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const PASSWORD = "DemoPass!12345";
const JSON_HDR = { "Content-Type": "application/json" };

const LOGIN_RATE = Number(__ENV.LOGIN_RATE || 2);
const scenarios = {
  browse: { executor: "constant-vus", vus: Number(__ENV.VUS || 50), duration: __ENV.DURATION || "60s", exec: "browse" },
};
if (LOGIN_RATE > 0) {
  scenarios.logins = { executor: "constant-arrival-rate", rate: LOGIN_RATE, timeUnit: "1s", duration: __ENV.DURATION || "60s", preAllocatedVUs: 5, exec: "loginOnly" };
}

export const options = {
  scenarios,
  thresholds: {
    "http_req_duration{scenario:browse}": ["p(95)<300"],
    "http_req_failed{scenario:browse}": ["rate<0.01"],
    "http_req_duration{name:login}": ["p(95)<1000"], // argon2 hashing is deliberately expensive
    checks: ["rate>0.99"],
    "http_req_duration{name:patients_me}": ["p(95)<10000"],
    "http_req_duration{name:doctors}": ["p(95)<10000"],
    "http_req_duration{name:slots}": ["p(95)<10000"],
    "http_req_duration{name:my_appointments}": ["p(95)<10000"],
    "http_req_duration{name:patient_search}": ["p(95)<10000"],
    "http_req_duration{name:patient_get}": ["p(95)<10000"],
    "http_req_duration{name:calendar}": ["p(95)<10000"],
    "http_req_duration{name:doctor_schedule}": ["p(95)<10000"],
    "http_req_duration{name:doctor_patients}": ["p(95)<10000"],
  },
};

function login(email, password) {
  const r = http.post(`${BASE}/api/auth/login`, JSON.stringify({ email, password }), { headers: JSON_HDR, tags: { name: "login" } });
  check(r, { "login 200": (x) => x.status === 200 });
  return r.status === 200 ? r.json("access_token") : null;
}

export function setup() {
  const tokens = {};
  for (const [k, email] of Object.entries({
    p1: "patient1@example.com", p2: "patient2@example.com", p3: "patient3@example.com",
    staff: "staff@hospital.example.com", d1: "doctor1@hospital.example.com",
  })) tokens[k] = login(email, PASSWORD);
  const auth = { headers: { Authorization: `Bearer ${tokens.staff}` } };
  const doctors = http.get(`${BASE}/api/doctors`, auth).json();
  const patients = http.get(`${BASE}/api/patients?size=3`, auth).json("items");
  return { tokens, doctorId: doctors[0].id, patientIds: patients.map((p) => p.id) };
}

const H = (t) => ({ headers: { Authorization: `Bearer ${t}` } });
const day = (n) => new Date(Date.now() + n * 86400000).toISOString().slice(0, 10);

export function browse(data) {
  const who = __VU % 3;
  if (who === 0) {
    const t = data.tokens[`p${(__VU % 3) + 1}`];
    check(http.get(`${BASE}/api/patients/me`, { ...H(t), tags: { name: "patients_me" } }), { ok: (r) => r.status === 200 });
    check(http.get(`${BASE}/api/doctors`, { ...H(t), tags: { name: "doctors" } }), { ok: (r) => r.status === 200 });
    check(http.get(`${BASE}/api/doctors/${data.doctorId}/slots?from=${day(0)}&to=${day(13)}`, { ...H(t), tags: { name: "slots" } }), { ok: (r) => r.status === 200 });
    check(http.get(`${BASE}/api/appointments`, { ...H(t), tags: { name: "my_appointments" } }), { ok: (r) => r.status === 200 });
  } else if (who === 1) {
    const t = data.tokens.staff;
    check(http.get(`${BASE}/api/patients?q=demo&size=20`, { ...H(t), tags: { name: "patient_search" } }), { ok: (r) => r.status === 200 });
    const pid = data.patientIds[__ITER % data.patientIds.length];
    check(http.get(`${BASE}/api/patients/${pid}`, { ...H(t), tags: { name: "patient_get" } }), { ok: (r) => r.status === 200 });
    check(http.get(`${BASE}/api/appointments?doctor_id=${data.doctorId}&from=${day(0)}&to=${day(6)}`, { ...H(t), tags: { name: "calendar" } }), { ok: (r) => r.status === 200 });
  } else {
    const t = data.tokens.d1;
    check(http.get(`${BASE}/api/appointments?from=${day(0)}&to=${day(6)}`, { ...H(t), tags: { name: "doctor_schedule" } }), { ok: (r) => r.status === 200 });
    check(http.get(`${BASE}/api/patients`, { ...H(t), tags: { name: "doctor_patients" } }), { ok: (r) => r.status === 200 });
  }
  sleep(1 + Math.random() * 2); // think time 1-3 s (a person reading a screen)
}

export function loginOnly() {
  login("patient1@example.com", PASSWORD);
}
