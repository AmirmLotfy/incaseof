import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "In Case Of — ICO",
    short_name: "ICO",
    description: "Monitor the plan, not the person.",
    start_url: "/",
    display: "standalone",
    background_color: "rgb(23, 26, 24)",
    theme_color: "rgb(23, 26, 24)",
    icons: [
      { src: "/images/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/images/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/images/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
