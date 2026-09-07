import type { Metadata } from "next";
import { IcoLogo } from "@/components/IcoLogo";

export const metadata: Metadata = {
  title: "Delete your account — In Case Of",
  description: "How to stop monitoring and delete an In Case Of account and its data.",
};

export default function DeleteAccountPage() {
  return (
    <main className="shell account-deletion-page">
      <a href="/" aria-label="In Case Of home" className="app-logo">
        <IcoLogo size={38} />
      </a>
      <p className="eyebrow">Account and data</p>
      <h1>Delete your account</h1>
      <p className="account-deletion-lead">
        Deleting your account stops every future check-in and escalation. Your plans,
        Circle, contact methods, history, and sign-in are then removed through a retryable
        process.
      </p>

      <section className="account-deletion-steps" aria-labelledby="delete-steps">
        <h2 id="delete-steps">Use the secure account screen</h2>
        <ol>
          <li>Open the web app and sign in to the account you want to delete.</li>
          <li>Find <strong>Delete account</strong> under Account.</li>
          <li>Type <span className="mono">DELETE</span> and confirm.</li>
        </ol>
        <a className="cta" href="/app#delete-account">Open account deletion</a>
      </section>

      <section className="account-deletion-steps" aria-labelledby="what-happens">
        <h2 id="what-happens">What happens next</h2>
        <ul>
          <li>Monitoring closes as soon as the request is accepted.</li>
          <li>Pending timers and escalation workflows are cancelled.</li>
          <li>Contact endpoints, plans, Circle records, and account data are removed.</li>
          <li>Your sign-in is deleted after cleanup succeeds.</li>
        </ul>
        <p>
          Keep the status screen open if you want to see progress. When sign-in stops
          working, identity deletion has completed.
        </p>
      </section>
    </main>
  );
}
