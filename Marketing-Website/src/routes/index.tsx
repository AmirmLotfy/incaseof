import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { Problem } from "@/components/landing/Problem";
import { DemoSentence } from "@/components/landing/DemoSentence";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Gemma } from "@/components/landing/Gemma";
import { Apk } from "@/components/landing/Apk";
import { Screens } from "@/components/landing/Screens";
import { Safety } from "@/components/landing/Safety";
import { Architecture } from "@/components/landing/Architecture";
import { Resources } from "@/components/landing/Resources";
import { Footer } from "@/components/landing/Footer";

export const Route = createFileRoute("/")({
  component: Index,
  head: () => ({
    meta: [
      { title: "In Case of — Gemma 4 Safety Agent" },
      {
        name: "description",
        content:
          "A local-first Android safety agent that turns natural language into trusted, user-approved action plans powered by Gemma 4. Built for the Kaggle Gemma 4 Good Hackathon.",
      },
      { property: "og:type", content: "website" },
      { property: "og:title", content: "In Case of — A safety agent for the moments you can't respond" },
      {
        property: "og:description",
        content:
          "Built for the Kaggle Gemma 4 Good Hackathon. Android-first, local-first, powered by Gemma 4.",
      },
      { property: "og:image", content: "/og/og-image.jpg" },
      { property: "og:url", content: "/" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "In Case of" },
      { name: "twitter:description", content: "Local-first safety plans powered by Gemma 4." },
      { name: "twitter:image", content: "/og/og-image.jpg" },
    ],
    links: [{ rel: "canonical", href: "/" }],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          name: "In Case of",
          applicationCategory: "UtilitiesApplication",
          operatingSystem: "Android",
          description:
            "Local-first Android safety agent powered by Gemma 4. Turns plain-language scenarios into user-approved safety workflows.",
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        }),
      },
    ],
  }),
});

function Index() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <main>
        <Hero />
        <Problem />
        <DemoSentence />
        <HowItWorks />
        <Gemma />
        <Apk />
        <Screens />
        <Safety />
        <Architecture />
        <Resources />
      </main>
      <Footer />
    </div>
  );
}
