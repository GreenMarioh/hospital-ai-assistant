import { RoleShell } from "@/components/Shell";

export default function ReceptionLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleShell
      role="staff"
      title="Reception console"
      nav={[
        { href: "/reception", label: "Patients" },
        { href: "/reception/calendar", label: "Calendar & booking" },
      ]}
    >
      {children}
    </RoleShell>
  );
}
