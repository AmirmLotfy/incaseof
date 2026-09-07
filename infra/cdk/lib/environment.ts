/**
 * Environment definitions.
 *
 * Demo data must never mix with real user data, so every environment is a separate stack
 * instance with its own table, schedules and queues. `demoTimeScale` is the only knob that
 * differs behaviourally, and it compresses the *schedule* only — never the logic.
 * See docs/DEMO.md.
 */

export type EnvName = "dev" | "demo" | "staging" | "prod";

export interface IcoEnvironment {
  readonly name: EnvName;
  /** Schedule compression. 1.0 is real time. 0.02 turns 10 minutes into 12 seconds. */
  readonly demoTimeScale: number;
  /** Whether the surface must display a persistent "Demo timing enabled" banner. */
  readonly showsDemoBanner: boolean;
  readonly region: string;
  /** Whether a new plan may reserve monitoring capacity in this environment. */
  readonly admissionsOpen: boolean;
  /** Per-account ceiling while the launch budget and throughput are being validated. */
  readonly maxActivePlansPerAccount: number;
  /**
   * Concurrency reserved for the action worker, or undefined to leave it unreserved.
   *
   * Reserving caps how many contacts can go out at once — a contact is not something to
   * parallelise for throughput, and a small ceiling keeps one incident from starving
   * every other person's escalation.
   *
   * Undefined in dev and demo because a *new* AWS account has a total concurrency quota
   * of 10 and requires 10 to stay unreserved, so reserving any at all fails the deploy
   * outright. The quota lifts with account age or on request; until then the cap is a
   * production concern, and low-traffic environments do not need it.
   */
  readonly reservedWorkerConcurrency?: number;
}

export const ENVIRONMENTS: Record<EnvName, IcoEnvironment> = {
  dev: {
    name: "dev",
    demoTimeScale: 1.0,
    showsDemoBanner: false,
    region: "us-east-1",
    admissionsOpen: true,
    maxActivePlansPerAccount: 3,
  },
  demo: {
    name: "demo",
    demoTimeScale: 0.02,
    showsDemoBanner: true,
    region: "us-east-1",
    admissionsOpen: true,
    maxActivePlansPerAccount: 3,
  },
  staging: {
    name: "staging",
    demoTimeScale: 1.0,
    showsDemoBanner: false,
    region: "us-east-1",
    admissionsOpen: false,
    maxActivePlansPerAccount: 3,
    reservedWorkerConcurrency: 10,
  },
  prod: {
    name: "prod",
    demoTimeScale: 1.0,
    showsDemoBanner: false,
    region: "us-east-1",
    admissionsOpen: false,
    maxActivePlansPerAccount: 3,
    reservedWorkerConcurrency: 20,
  },
};

/** Any environment that compresses time must say so on screen. */
export function assertBannerInvariant(env: IcoEnvironment): void {
  if (env.demoTimeScale !== 1.0 && !env.showsDemoBanner) {
    throw new Error(
      `Environment "${env.name}" compresses time but does not show the demo banner. ` +
        `A surface that silently runs on a different clock is misleading.`,
    );
  }
}
