"use client";

import { Badge, Button, statusTone } from "./ui";
import type { Schemas } from "@/lib/api";
import { addDays, fmtTime, localDate, localHM, weekdayLabel, weekStart } from "@/lib/time";

export type Appt = Schemas["AppointmentOut"];
const HOURS = Array.from({ length: 12 }, (_, i) => i + 7); // 07:00-18:59

export function Calendar({
  appointments,
  date,
  view,
  onDateChange,
  onViewChange,
  onSelect,
  showPatient = true,
  showDoctor = false,
}: {
  appointments: Appt[];
  date: string;
  view: "day" | "week";
  onDateChange: (d: string) => void;
  onViewChange: (v: "day" | "week") => void;
  onSelect?: (a: Appt) => void;
  showPatient?: boolean;
  showDoctor?: boolean;
}) {
  const days = view === "day" ? [date] : Array.from({ length: 7 }, (_, i) => addDays(weekStart(date), i));
  const step = view === "day" ? 1 : 7;
  const active = appointments.filter((a) => a.status !== "cancelled");
  const cell = (day: string, hour: number) =>
    active.filter((a) => localDate(a.starts_at) === day && localHM(a.starts_at).h === hour);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Button
          variant="secondary"
          onClick={() => onDateChange(addDays(date, -step))}
          aria-label={`Previous ${view}`}
        >
          ‹ Prev
        </Button>
        <Button
          variant="secondary"
          onClick={() => onDateChange(addDays(date, step))}
          aria-label={`Next ${view}`}
        >
          Next ›
        </Button>
        <input
          type="date"
          aria-label="Go to date"
          value={date}
          onChange={(e) => e.target.value && onDateChange(e.target.value)}
          className="rounded border border-slate-500 px-2 py-1.5 text-sm"
        />
        <div className="ml-auto flex gap-1" role="group" aria-label="Calendar view">
          {(["day", "week"] as const).map((v) => (
            <Button
              key={v}
              variant={view === v ? "primary" : "secondary"}
              aria-pressed={view === v}
              onClick={() => onViewChange(v)}
            >
              {v === "day" ? "Day" : "Week"}
            </Button>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] border-collapse text-sm">
          <caption className="sr-only">
            Appointments for {view === "day" ? weekdayLabel(date) : `week of ${weekdayLabel(days[0])}`}
          </caption>
          <thead>
            <tr>
              <th scope="col" className="w-16 border border-slate-300 bg-slate-100 p-1 text-left">
                Time
              </th>
              {days.map((d) => (
                <th key={d} scope="col" className="border border-slate-300 bg-slate-100 p-1 text-left">
                  {weekdayLabel(d)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {HOURS.map((h) => (
              <tr key={h}>
                <th scope="row" className="border border-slate-300 bg-slate-50 p-1 text-left font-normal">
                  {String(h).padStart(2, "0")}:00
                </th>
                {days.map((d) => (
                  <td key={d} className="h-14 border border-slate-300 p-1 align-top">
                    {cell(d, h).map((a) => (
                      <button
                        key={a.id}
                        onClick={() => onSelect?.(a)}
                        className="mb-1 block w-full rounded border border-blue-300 bg-blue-50 p-1 text-left text-xs hover:bg-blue-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                      >
                        <span className="font-semibold">{fmtTime(a.starts_at)}</span>{" "}
                        {showPatient && a.patient_name}
                        {showDoctor && <span className="block text-slate-700">{a.doctor_name}</span>}{" "}
                        <Badge tone={statusTone(a.status)}>{a.status}</Badge>
                      </button>
                    ))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
