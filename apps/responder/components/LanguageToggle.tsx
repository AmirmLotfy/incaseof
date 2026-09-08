import { copy, type Locale } from "@/lib/i18n";

export function LanguageToggle({ locale, onChange }: { locale: Locale; onChange: (locale: Locale) => void }) {
  const next = locale === "ar" ? "en" : "ar";
  return (
    <button className="language-toggle" type="button" onClick={() => onChange(next)} lang={next}>
      {copy[locale].switchLanguage}
    </button>
  );
}
