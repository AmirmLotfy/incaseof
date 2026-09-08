import type { Metadata } from "next";
import { ConsentEntry } from "@/components/ConsentEntry";

export const metadata: Metadata = {
  title: "Circle invitation — In Case Of",
  robots: { index: false, follow: false },
};

export function generateStaticParams() {
  return [{ token: "__token" }];
}

export const dynamicParams = false;

export default async function InvitationPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <ConsentEntry initialToken={token} />;
}
