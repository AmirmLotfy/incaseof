import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="border-t hairline pt-16 pb-10">
      <div className="mx-auto max-w-7xl px-6">
        <div className="flex flex-col items-start justify-between gap-10 md:flex-row md:items-center">
          <div className="max-w-md">
            <Logo />
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Local-first safety plans for the moments you can&apos;t respond.
              Built for the Kaggle Gemma 4 Good Hackathon.
            </p>
          </div>
          <ul className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
            <li><a href="https://github.com/AmirmLotfy/incaseof" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground">GitHub</a></li>
            <li><a href="#resources" className="text-muted-foreground hover:text-foreground">Demo Video</a></li>
            <li><a href="/downloads/in-case-of-v1.apk" download className="text-muted-foreground hover:text-foreground">APK</a></li>
            <li><a href="https://github.com/AmirmLotfy/incaseof/blob/main/KAGGLE_WRITEUP.md" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground">Writeup</a></li>
          </ul>
        </div>
        <div className="mt-12 border-t hairline pt-6 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          Prototype only. Not a replacement for emergency services.
        </div>
      </div>
    </footer>
  );
}
