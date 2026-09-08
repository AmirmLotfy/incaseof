# Agents for Humans: Engineering an Idempotent Contingency Workflow on AWS

Retries are normal in distributed systems. In a contingency product, however, a duplicate retry can
become a duplicate message to a worried family member, while a dropped event can become no message
at all.

**In Case Of (ICO)** treats at-least-once delivery as a design input rather than an edge case.

## Start with durable state

Amazon EventBridge Scheduler owns Expected Moment timers. When a Moment becomes due, a Python AWS
Lambda function creates exactly one Alert and starts an AWS Step Functions Standard workflow.

The workflow asks deterministic domain code for the next decision:

- dispatch one rung of the escalation ladder;
- wait until an offset or checking-lease expiry;
- advance after a confirmed “could not reach” response; or
- close after explicit resolution.

The state machine does not interpret language and does not resolve contact endpoints. Those jobs
belong to separate, narrower components.

## Persist intent before delivery

One of our early failure cases exposed a dangerous ordering problem: claiming an action before
queue submission could lose it if SQS enqueueing failed.

The repair was a transactional outbox. Domain state, workflow progress, and a durable action intent
are persisted together in DynamoDB. A relay submits pending intents to SQS and retries safely. A
scheduled recovery pass picks up anything left behind after a crash.

This means the system can answer a basic question after any interruption: **what did we intend to
do?**

## Give every effect a stable identity

Each delivery action is keyed by the Alert, escalation step, and attempt. DynamoDB conditional
writes provide durable ownership and outcome state. Repeated Scheduler events, Step Functions
retries, concurrent workers, and SQS redelivery converge on the same action record.

A worker crash before provider invocation releases recoverable work. A confirmed provider
acceptance prevents another provider call. A timeout after an unknown provider outcome enters
reconciliation instead of blindly resending or falsely claiming delivery.

The distinction is essential:

- **queued** means ICO has durable intent;
- **accepted** means the provider accepted the request;
- **delivered** requires a real provider or carrier receipt;
- **unknown** requires reconciliation;
- **failed** means a definite failure that policy may retry.

An Amazon SNS message ID is evidence of provider acceptance. It is not evidence that a handset
received the message.

## Reauthorize at the last moment

Authorization can change while work waits in a queue. Immediately before any delivery, the worker
rechecks:

- tenant and pinned recipient membership;
- current consent and channel permission;
- the immutable Plan Version attached to the Alert;
- current Alert state;
- any active checking lease; and
- the exact action identity and provider outcome.

Withdrawing consent after enqueueing therefore blocks the provider call. Resolving an Alert while a
delivery is pending also stops stale escalation.

## Model human coordination as a lease

A responder tapping **I’m checking** needs enough time to call or visit, but that action cannot
silently stop the workflow forever. ICO creates a ten-minute lease. While it is active, the next
Circle contact is paused. If the responder reports that they could not reach the subject, escalation
continues immediately. If the lease expires, the deterministic ladder resumes.

Only an explicit outcome moves the Alert to `RESOLVED` and cancels remaining work.

## Test the failure sequences, then show the real path

The final Python suite contains **467 collected tests**. The regression cases cover duplicate and
concurrent delivery, queue submission failure, worker crash, consent withdrawal after enqueue,
provider timeout after acceptance, recipient changes, resolution races, and subject delivery
through mocked provider clients.

The public hackathon tenant runs the same EventBridge Scheduler, Step Functions, DynamoDB, SQS,
worker, lease, and audit code on an accelerated clock. Only the final external delivery is replaced
by a named safe sink.

On September 9, a fresh public drill produced an 11-event timeline:

1. Moment due.
2. State entered self contact.
3. Three action intents were queued and accepted through the safe sink.
4. State advanced to Circle escalation.
5. A responder claimed the Alert.
6. The responder explicitly verified contact.

The final state was `RESOLVED`, and the ladder stopped. No private phone number or live recipient
was used.

Reliable agents need more than a successful happy path. They need a durable explanation for every
effect, every retry, and every uncertain outcome. That is how ICO closes uncertainty without
creating new uncertainty of its own.

## Inspect and try it

- [Run the synthetic live judge demo](https://incaof.com/demo/)
- [Read the open-source repository](https://github.com/AmirmLotfy/incaseof)
- [View the submitted project on Devpost](https://devpost.com/software/in-case-of-ygk5uj)

Built for the **Agents for Humans Hackathon**, Everyday Agents track.
