"use client";

import { useCallback, useEffect, useState } from "react";
import type { Locale } from "@/lib/i18n";

function requestedLocale(): Locale {
  const query = new URLSearchParams(window.location.search).get("lang");
  if (query === "ar" || query === "en") return query;
  return navigator.language.toLowerCase().startsWith("ar") ? "ar" : "en";
}

export function useResponderLocale(): [Locale, (locale: Locale) => void] {
  const [locale, setLocaleState] = useState<Locale>("en");

  const apply = useCallback((next: Locale) => {
    document.documentElement.lang = next;
    document.documentElement.dir = next === "ar" ? "rtl" : "ltr";
    setLocaleState(next);
  }, []);

  useEffect(() => apply(requestedLocale()), [apply]);

  const setLocale = useCallback((next: Locale) => {
    const url = new URL(window.location.href);
    url.searchParams.set("lang", next);
    window.history.replaceState(null, "", url);
    apply(next);
  }, [apply]);

  return [locale, setLocale];
}
