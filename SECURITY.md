# Security policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/AmirmLotfy/incaseof/security/advisories/new)
rather than opening a public issue.

Include what you found, how to reproduce it, and what an attacker could achieve. We will
acknowledge your report and keep you updated on the fix.

## Why this matters here

In Case of knows who is alone and when, and who their trusted contacts are. A vulnerability in
this system is a stalking and physical-safety risk, not only a privacy one. We take reports on
that basis.

Areas we consider especially sensitive:

- Responder token forgery, replay, or scope escalation beyond a single Alert
- Any path that lets the agent contact an endpoint it was not authorized to contact
- Cross-account access to another person's Alert, Plan, or Circle
- Unauthorized context release, particularly location
- Anything that causes an Alert to close without a valid stop condition

## Scope

This is a hackathon project. **It is not an emergency service** and is not a substitute for local
emergency services, medical care, or professional monitoring.

For the engineering security design, see [`docs/SECURITY.md`](docs/SECURITY.md).
