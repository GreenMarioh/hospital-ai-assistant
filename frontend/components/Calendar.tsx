"use client";

import { Badge, Button, cx, statusTone, statusLabel } from "./ui";
import type { Schemas } from "@/lib/api";
import { addDays, fmtTime, localDate, localHM, todayLocal, weekdayLabel, weekStart } from "@/lib/time";

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
  const today = todayLocal();
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
          <span aria-hidden="true">‹</span> Prev
        </Button>
        <Button
          variant="secondary"
          onClick={() => onDateChange(addDays(date, step))}
          aria-label={`Next ${view}`}
        >
          Next <span aria-hidden="true">›</span>
        </Button>
        <input
          type="date"
          aria-label="Go to date"
          value={date}
          onChange={(e) => e.target.value && onDateChange(e.target.value)}
          className="rounded-[5px] border border-slate-400 bg-white px-2.5 py-[7px] text-sm text-navy-950 hover:border-navy-400 focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-100"
        />
        <div
          className="ml-auto flex rounded-[6px] border border-navy-200 bg-white p-0.5"
          role="group"
          aria-label="Calendar view"
        >
          {(["day", "week"] as const).map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={view === v}
              onClick={() => onViewChange(v)}
              className={cx(
                "rounded-[4px] px-3.5 py-1.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-600",
                view === v ? "bg-navy-800 text-white" : "text-navy-800 hover:bg-navy-50",
              )}
            >
              {v === "day" ? "Day" : "Week"}
            </button>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto rounded-md border border-line">
        <table className="w-full min-w-[520px] border-collapse text-sm">
          <caption className="sr-only">
            Appointments for {view === "day" ? weekdayLabel(date) : `week of ${weekdayLabel(days[0])}`}
          </caption>
          <thead>
            <tr>
              <th
                scope="col"
                className="w-16 border-b border-line bg-paper px-2 py-2 text-left text-xs font-medium text-slate-600"
              >
                Time
              </th>
              {days.map((d) => (
                <th
                  key={d}
                  scope="col"
                  className={cx(
                    "border-b border-l border-line px-2 py-2 text-left text-xs font-semibold",
                    d === today && view === "week"
                      ? "bg-marigold-100 text-navy-900"
                      : "bg-paper text-navy-800",
                  )}
                >
                  {weekdayLabel(d)}
                  {d === today && <span className="ml-1.5 font-normal text-[#5C3D06]">today</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {HOURS.map((h) => (
              <tr key={h}>
                <th
                  scope="row"
                  className="border-t border-line px-2 py-1.5 text-left align-top text-xs font-normal text-slate-600"
                >
                  {String(h).padStart(2, "0")}:00
                </th>
                {days.map((d) => (
                  <td
                    key={d}
                    className={cx(
                      "h-14 border-l border-t border-line p-1 align-top",
                      d === today && view === "week" && "bg-marigold-100/40",
                    )}
                  >
                    {cell(d, h).map((a) => (
                      <button
                        key={a.id}
                        onClick={() => onSelect?.(a)}
                        className="mb-1 block w-full rounded-[4px] border-l-[3px] border-navy-700 bg-navy-50 px-1.5 py-1 text-left text-xs leading-snug text-navy-950 transition-colors hover:bg-navy-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-600"
                      >
                        <span className="num font-semibold text-navy-800">{fmtTime(a.starts_at)}</span>{" "}
                        {showPatient && a.patient_name}
                        {showDoctor && <span className="block text-slate-700">{a.doctor_name}</span>}{" "}
                        <Badge tone={statusTone(a.status)}>{statusLabel(a.status)}</Badge>
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
