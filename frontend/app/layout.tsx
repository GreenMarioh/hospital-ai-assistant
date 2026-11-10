import "@fontsource-variable/public-sans";
import "@fontsource-variable/source-serif-4";
import "./globals.css";
import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "AI Hospital Assistant",
  description: "Patient management, scheduling and AI-assisted triage",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
