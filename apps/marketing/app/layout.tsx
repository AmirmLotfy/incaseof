import type { Metadata, Viewport } from "next";
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
  metadataBase: new URL("https://incaof.com"),
  title: "In Case of — Someone notices.",
  description: "Tell In Case of what should happen. If it doesn't, it knows who to reach and when to keep going.",
  applicationName: "In Case Of — ICO",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "16x16 32x32 48x48" },
      { url: "/images/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/images/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/images/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  openGraph: {
    type: "website",
    url: "https://incaof.com/",
    siteName: "In Case Of — ICO",
    title: "In Case Of — Someone notices.",
    description: "Monitor the plan, not the person. Safe contingency workflows governed on AWS.",
    images: [{ url: "/opengraph-image.png", width: 1200, height: 630, alt: "In Case Of — Someone notices" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "In Case Of — Someone notices.",
    description: "Monitor the plan, not the person. Safe contingency workflows governed on AWS.",
    images: ["/opengraph-image.png"],
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "rgb(23, 26, 24)",
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
