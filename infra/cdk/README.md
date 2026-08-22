# Infrastructure

```bash
npm run synth -w @incaseof/infra              # dev (default)
npx cdk synth -c env=demo                     # demo environment
```

Deployment requires the AWS CLI and a scoped deployment role — see `docs/SECURITY.md` §4.
Nothing here is deployed during Phase 0.

**Every resource is defined here.** Nothing is created by hand in the console: the
hackathon requires that the environment can be reconstructed from the repository, and a
console-created resource is invisible to that claim.
