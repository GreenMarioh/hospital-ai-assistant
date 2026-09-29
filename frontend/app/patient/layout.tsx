import { RoleShell } from "@/components/Shell";

export default function PatientLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleShell
      role="patient"
      title="Patient portal"
      nav={[
        { href: "/patient", label: "Home" },
        { href: "/patient/assistant", label: "Symptom check & FAQ" },
        { href: "/patient/book", label: "Book appointment" },
        { href: "/patient/appointments", label: "My appointments" },
        { href: "/patient/records", label: "My records" },
      ]}
    >
      {children}
    </RoleShell>
  );
}
