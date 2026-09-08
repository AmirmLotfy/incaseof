import type { Metadata } from "next";
import { IcoLogo } from "@/components/IcoLogo";
import { DeleteAccountContent } from "@/components/DeleteAccountContent";

export const metadata: Metadata = {
  title: "Delete your account — In Case Of",
  description: "How to stop monitoring and delete an In Case Of account and its data.",
};

export default function DeleteAccountPage() {
  return (
    <main className="shell account-deletion-page">
      <a href="/" aria-label="In Case Of home" className="app-logo">
        <IcoLogo size={38} />
      </a>
      <DeleteAccountContent />
    </main>
  );
}
