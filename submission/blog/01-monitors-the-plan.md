# Agents for Humans: Why ICO Monitors the Plan, Not the Person

Independence and reassurance are often presented as opposites. A person who lives alone,
recovers at home, commutes late, or takes a solo trip is usually offered two familiar tools:
continuous tracking, or an emergency button that only helps when they can press it.

We built **In Case Of (ICO)** around a quieter third option:

> Monitor the plan, not the person.

ICO watches a promise someone deliberately creates. It does not watch their life.

## Start with an expected moment

An **Expected Moment** is an ordinary commitment:

- “I will check in at nine tonight.”
- “I should be home by six.”
- “I am hiking until sunset.”
- “Remind me to confirm after my appointment.”

While that moment remains in the future, ICO does nothing. It does not collect a live route,
listen to a microphone, watch a camera, or infer danger from behavior. If the expected moment
passes unresolved, ICO follows an escalation plan the subject reviewed in advance.

That word—**unresolved**—matters. Being late does not mean someone is in danger. Software should
not manufacture certainty where none exists.

## Make the plan literal before activation

Natural language is useful for describing an intention, but it can hide ambiguity. ICO turns the
request into a preview with explicit timing, grace periods, contact roles, and channels. The
subject sees exactly what will happen before saving anything. Activation is a separate action.

The preview is checked again by deterministic validation:

- Is the time zone valid?
- Is the recurrence bounded?
- Has every required Circle member consented?
- Are the selected channels ready?
- Does the requested action comply with policy?

The agent may propose structure. It cannot activate a plan, create a timer, or contact anyone.

## Acknowledged is not resolved

When a Moment becomes due, ICO starts with the subject. If there is still no answer after the
configured grace period, it reaches the subject again and then moves through the approved Circle.

A responder receives one short-lived link for one Alert. Tapping **I’m checking** creates a
temporary lease. It pauses the next contact so two worried people do not duplicate effort, but the
Alert remains open. If that lease expires, escalation resumes automatically.

Only an explicit outcome closes the loop:

- The subject confirms they are okay.
- A responder confirms direct contact.
- A responder reports that they could not reach the subject, which advances the ladder instead of
  pretending the situation is resolved.

This small distinction changed the entire product. Acknowledgement is coordination. Resolution is
evidence of an outcome.

## Privacy through removed capability

The architecture follows the same promise as the interface. Every Alert is pinned to the immutable
Plan Version that created it. Contact endpoints are encrypted and resolved only inside the delivery
worker, immediately before an authorized send. The Strands agent sees abstract roles such as
`PRIMARY` and `BACKUP`; it never receives a phone number, email address, or arbitrary URL.

That is stronger than asking a model to behave carefully. The capability is absent from its tool
surface.

The responder page also discloses as little as possible. A signed, expiring token grants only the
actions needed for one Alert. The responder does not need an account and cannot browse the
subject’s history or Circle.

## Proving the complete loop

The public judge demo uses synthetic people and an accelerated clock, but it exercises the deployed
AWS path: DynamoDB, EventBridge Scheduler, Step Functions, SQS, the delivery worker, the signed
responder room, and the audit timeline. The last external delivery edge is redirected to a named
safe sink so a judge can test the workflow without sending a real message.

On September 9, we reran the public path from plan compilation through an 11-event audit trail,
responder claim, checking lease, and explicit resolution. The Alert reached `RESOLVED`, and the
contact ladder stopped.

The product is intentionally calm. Most days, nothing should happen. Its value appears in the
unusual moment when a small promise is missed and uncertainty needs to be closed without turning a
person’s life into a surveillance feed.

For human-centered agents, restraint is an engineered capability: know when to wait, know what not
to collect, and know when judgment belongs to a person.

## Try the project

- [Run the synthetic live judge demo](https://incaof.com/demo/)
- [Read the open-source repository](https://github.com/AmirmLotfy/incaseof)
- [View the submitted project on Devpost](https://devpost.com/software/in-case-of-ygk5uj)

Built for the **Agents for Humans Hackathon**, Everyday Agents track.
