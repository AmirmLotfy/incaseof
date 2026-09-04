import type { Metadata } from "next";
import { IcoLogo } from "@/components/IcoLogo";
import { WebApp } from "@/components/WebApp";

export const metadata: Metadata = {
  title: "Your plans — In Case Of",
  description: "Create, review and test your In Case Of contingency plans.",
  robots: { index: false, follow: false },
};

export default function AppPage() {
  return (
    <main className="shell app-shell">
      <a href="/" aria-label="In Case Of home" className="app-logo"><IcoLogo size={38} /></a>
      <WebApp />
    </main>
  );
}
