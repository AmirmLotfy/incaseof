# Agents for Humans: Why ICO Monitors the Plan, Not the Person

Independence and reassurance are often presented as opposites. A person who lives alone,
commutes late or takes a solo trail run is offered two familiar tools: continuous tracking,
or an emergency button that works only when they can press it. We built In Case Of - ICO
around a third idea: monitor an expectation, not a person.

An **Expected Moment** is a promise someone chooses to make: "I will check in at nine" or
"I should be home by six." While that moment remains in the future, ICO does nothing. It
does not collect a live route, listen to a microphone or infer danger from behavior. If the
moment passes unresolved, it starts a reviewed escalation plan.

This distinction shaped the product language. ICO never says someone is unsafe merely
because they are late. Its state is **unresolved**, not "danger." It first asks the subject
for confirmation. Only after the configured grace period can it contact a Circle of people
who already consented. A friend tapping **I'm checking** receives a temporary lease, but
the Alert remains open. If the lease expires, escalation resumes. Acknowledgment is useful
coordination; it is not evidence of an outcome.

It also shaped the data model. Each Alert is pinned to the immutable Plan Version that
created it. Context is released according to explicit rules. Contact endpoints are resolved
only inside the delivery worker, after tenant, consent, version and state checks. The agent
never receives a phone number, email address or arbitrary URL.

The result feels less like a surveillance dashboard and more like a contingency card. Most
days, the interface should be quiet. The meaningful measure is not engagement; it is how
clearly ICO closes an unusual moment without inventing a conclusion.

For human-centered agents, restraint is not an absence of capability. It is a capability we
designed deliberately: know when to wait, know what not to collect, and know when judgment
belongs to a person.

_Before publication: add the accepted live demo URL, repository URL, one real screenshot,
and an architecture image. Do not add a live claim until the release evidence passes._
