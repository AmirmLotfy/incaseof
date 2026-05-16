export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center ${className}`}>
      <picture>
        <source srcSet="/logo-wide.webp" type="image/webp" />
        <img
          src="/logo-wide.png"
          alt="In Case Of logo"
          className="h-8 w-auto"
          width={200}
          height={113}
          decoding="async"
        />
      </picture>
    </span>
  );
}

