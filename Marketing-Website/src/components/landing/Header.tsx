import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { Logo } from "./Logo";

const NAV = [
  { href: "#problem", label: "Problem" },
  { href: "#how", label: "How it works" },
  { href: "#gemma", label: "Gemma 4" },
  { href: "#demo", label: "Demo" },
  { href: "#apk", label: "APK" },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all ${
        scrolled ? "glass border-b hairline" : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <a href="#top" className="flex items-center" aria-label="In Case of — home">
          <Logo />
        </a>
        <nav className="hidden items-center gap-8 md:flex">
          {NAV.map((n) => (
            <a
              key={n.href}
              href={n.href}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {n.label}
            </a>
          ))}
        </nav>
        <a
          href="/downloads/in-case-of-v1.apk"
          download
          className="inline-flex items-center gap-2 rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background transition-transform active:scale-95"
        >
          <Download className="size-3.5" />
          Download APK
        </a>
      </div>
    </header>
  );
}
