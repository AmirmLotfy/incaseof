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
}

export const ENVIRONMENTS: Record<EnvName, IcoEnvironment> = {
  dev: { name: "dev", demoTimeScale: 1.0, showsDemoBanner: false, region: "us-east-1" },
  demo: { name: "demo", demoTimeScale: 0.02, showsDemoBanner: true, region: "us-east-1" },
  staging: { name: "staging", demoTimeScale: 1.0, showsDemoBanner: false, region: "us-east-1" },
  prod: { name: "prod", demoTimeScale: 1.0, showsDemoBanner: false, region: "us-east-1" },
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
