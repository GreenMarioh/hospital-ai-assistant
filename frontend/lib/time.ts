export const HOSPITAL_TZ = process.env.NEXT_PUBLIC_HOSPITAL_TZ ?? "Asia/Kolkata";

export function fmtDateTime(iso: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: HOSPITAL_TZ,
  }).format(new Date(iso));
}

export function fmtTime(iso: string) {
  return new Intl.DateTimeFormat("en-GB", {
    timeStyle: "short",
    timeZone: HOSPITAL_TZ,
  }).format(new Date(iso));
}

/** YYYY-MM-DD of an instant in the hospital timezone. */
export function localDate(iso: string | Date) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: HOSPITAL_TZ }).format(new Date(iso));
}

export function todayLocal() {
  return localDate(new Date());
}

export function addDays(date: string, days: number) {
  const d = new Date(`${date}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Monday of the week containing `date`. */
export function weekStart(date: string) {
  const d = new Date(`${date}T12:00:00Z`);
  const dow = (d.getUTCDay() + 6) % 7;
  return addDays(date, -dow);
}

export function weekdayLabel(date: string) {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${date}T12:00:00Z`));
}

/** Hour (0-23) and minute of an instant in the hospital timezone. */
export function localHM(iso: string) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    hour: "numeric",
    minute: "numeric",
    hourCycle: "h23",
    timeZone: HOSPITAL_TZ,
  }).formatToParts(new Date(iso));
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value ?? 0);
  return { h: get("hour"), m: get("minute") };
}
