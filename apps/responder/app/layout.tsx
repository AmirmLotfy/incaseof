import type { Metadata } from "next";
import { Public_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// Public Sans + IBM Plex Mono. Deliberately no serif: the editorial-serif-on-beige
// treatment reads as generic AI-startup. See docs/design/DESIGN.md.
const publicSans = Public_Sans({
  subsets: ["latin"],
  variable: "--font-public-sans",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "In Case of",
  description: "Respond to a check-in request.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${publicSans.variable} ${plexMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
