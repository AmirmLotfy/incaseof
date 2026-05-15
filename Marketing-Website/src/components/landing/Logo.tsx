export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <img
        src="/app-icon.png"
        alt="In Case Of app icon"
        className="size-8 rounded-[10px] shadow-sm"
        width={32}
        height={32}
      />
      <span className="font-display text-[15px] font-semibold tracking-tight">
        In Case of
      </span>
    </span>
  );
}
