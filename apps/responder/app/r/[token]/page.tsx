import type { Metadata } from "next";
import { ResponderEntry } from "@/components/ResponderEntry";

export const metadata: Metadata = {
  title: "In Case Of",
  robots: { index: false, follow: false },
};

// CloudFront rewrites every /r/{token} request to this exported shell. The client reads
// the original browser path; the token never becomes part of a build artifact.
export function generateStaticParams() {
  return [{ token: "__token" }];
}

export const dynamicParams = false;

export default async function IncidentPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <ResponderEntry initialToken={token} />;
}
