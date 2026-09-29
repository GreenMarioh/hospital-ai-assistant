import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Calendar, type Appt } from "@/components/Calendar";
import { ChatInput, ChatLog } from "@/components/Chat";
import { AiDisclaimer, Alert, Empty, ErrorState, Field } from "@/components/ui";

const appt = (over: Partial<Appt> = {}): Appt => ({
  id: "1",
  patient_id: "p",
  doctor_id: "d",
  starts_at: "2026-09-30T04:30:00Z", // 10:00 Asia/Kolkata
  ends_at: "2026-09-30T05:00:00Z",
  status: "booked",
  reason: null,
  patient_name: "Ada Lovelace",
  doctor_name: "Dr. Who",
  ...over,
});

describe("Calendar", () => {
  it("places appointments in the hospital-time hour row and hides cancelled ones", () => {
    render(
      <Calendar
        appointments={[appt(), appt({ id: "2", status: "cancelled", patient_name: "Cancelled Person" })]}
        date="2026-09-30"
        view="day"
        onDateChange={() => {}}
        onViewChange={() => {}}
      />,
    );
    const row = screen.getByRole("row", { name: /10:00/ });
    expect(row).toHaveTextContent("Ada Lovelace");
    expect(screen.queryByText(/Cancelled Person/)).not.toBeInTheDocument();
  });

  it("navigates by day/week and switches view", async () => {
    const onDate = vi.fn();
    const onView = vi.fn();
    render(
      <Calendar
        appointments={[]}
        date="2026-09-30"
        view="week"
        onDateChange={onDate}
        onViewChange={onView}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /next week/i }));
    expect(onDate).toHaveBeenCalledWith("2026-10-07");
    await userEvent.click(screen.getByRole("button", { name: "Day" }));
    expect(onView).toHaveBeenCalledWith("day");
    expect(screen.getAllByRole("columnheader")).toHaveLength(8); // time + 7 days
  });

  it("reports the selected appointment", async () => {
    const onSelect = vi.fn();
    render(
      <Calendar
        appointments={[appt()]}
        date="2026-09-30"
        view="day"
        onDateChange={() => {}}
        onViewChange={() => {}}
        onSelect={onSelect}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Ada Lovelace/ }));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "1" }));
  });
});

describe("Chat", () => {
  it("renders messages in a live log with speaker labels", () => {
    render(
      <ChatLog
        messages={[
          { role: "user", text: "hi" },
          { role: "assistant", text: "hello" },
        ]}
        busy={false}
      />,
    );
    expect(screen.getByRole("log")).toHaveTextContent("You: hi");
    expect(screen.getByRole("log")).toHaveTextContent("Assistant: hello");
  });

  it("sends trimmed input and clears the box; ignores blanks", async () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} label="Message" />);
    const box = screen.getByLabelText("Message");
    await userEvent.type(box, "   {enter}");
    expect(onSend).not.toHaveBeenCalled();
    await userEvent.type(box, " chest ache {enter}");
    expect(onSend).toHaveBeenCalledWith("chest ache");
    expect(box).toHaveValue("");
  });
});

describe("ui primitives", () => {
  it("Field links label, hint and error for assistive tech", () => {
    render(<Field label="Email" error="Required" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Required");
  });
  it("alerts use the right live-region roles", () => {
    render(
      <>
        <Alert kind="error">bad</Alert>
        <Alert kind="emergency">call now</Alert>
        <Alert kind="info">fyi</Alert>
      </>,
    );
    expect(screen.getAllByRole("alert")).toHaveLength(2);
    expect(screen.getByRole("status")).toHaveTextContent("fyi");
  });
  it("shows the AI disclaimer and error/empty states", async () => {
    const retry = vi.fn();
    render(
      <>
        <AiDisclaimer />
        <Empty>Nothing here</Empty>
        <ErrorState error={new Error("Boom")} retry={retry} />
      </>,
    );
    expect(screen.getAllByText(/requires clinician review/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(retry).toHaveBeenCalled();
  });
});
