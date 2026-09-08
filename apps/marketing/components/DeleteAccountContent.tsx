"use client";

import { LanguageToggle } from "./LanguageToggle";
import { useLocale } from "./useLocale";
import { webCopy } from "@/lib/i18n";

export function DeleteAccountContent() {
  const [locale, setLocale] = useLocale();
  const words = webCopy[locale];
  return (
    <>
      <LanguageToggle locale={locale} onChange={setLocale} />
      <p className="eyebrow">{words.accountData}</p>
      <h1>{words.deletePageTitle}</h1>
      <p className="account-deletion-lead">{words.deletePageLead}</p>

      <section className="account-deletion-steps" aria-labelledby="delete-steps">
        <h2 id="delete-steps">{words.secureAccountScreen}</h2>
        <ol>{words.deleteInstructions.map((step) => <li key={step}>{step}</li>)}</ol>
        <a className="cta" href={`/app?lang=${locale}#delete-account`}>{words.openDeletion}</a>
      </section>

      <section className="account-deletion-steps" aria-labelledby="what-happens">
        <h2 id="what-happens">{words.whatNext}</h2>
        <ul>{words.deleteOutcomes.map((outcome) => <li key={outcome}>{outcome}</li>)}</ul>
        <p>{words.deletionStatusHelp}</p>
      </section>
    </>
  );
}
