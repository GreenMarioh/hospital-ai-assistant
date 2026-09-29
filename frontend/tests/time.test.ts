import { describe, expect, it } from "vitest";
import { addDays, localDate, localHM, weekStart, weekdayLabel } from "@/lib/time";

describe("time helpers", () => {
  it("adds days across month boundaries", () => {
    expect(addDays("2026-01-31", 1)).toBe("2026-02-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });
  it("finds the Monday of a week", () => {
    expect(weekStart("2026-09-30")).toBe("2026-09-28"); // Wednesday -> Monday
    expect(weekStart("2026-09-28")).toBe("2026-09-28");
    expect(weekStart("2026-10-04")).toBe("2026-09-28"); // Sunday belongs to the previous Monday
  });
  it("renders instants in the hospital timezone, not the browser's", () => {
    // 21:00 UTC is 02:30 next day in Asia/Kolkata (UTC+5:30)
    expect(localDate("2026-09-29T21:00:00Z")).toBe("2026-09-30");
    expect(localHM("2026-09-29T21:00:00Z")).toEqual({ h: 2, m: 30 });
  });
  it("labels weekdays", () => {
    expect(weekdayLabel("2026-09-30")).toMatch(/Wed/);
  });
});
