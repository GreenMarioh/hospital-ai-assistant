import { RoleShell } from "@/components/Shell";

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleShell
      role="doctor"
      title="Doctor workspace"
      nav={[
        { href: "/doctor", label: "My schedule" },
        { href: "/doctor/patients", label: "My patients" },
      ]}
    >
      {children}
    </RoleShell>
  );
}
