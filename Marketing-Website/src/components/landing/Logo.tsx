export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center ${className}`}>
      <img
        src="/logo-wide.png"
        alt="In Case Of logo"
        className="h-8 w-auto"
        width={56}
        height={32}
      />
    </span>
  );
}
