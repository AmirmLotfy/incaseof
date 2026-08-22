import { Stack, type StackProps, Tags } from "aws-cdk-lib";
import type { Construct } from "constructs";
import { assertBannerInvariant, type IcoEnvironment } from "./environment.js";

export interface IcoStackProps extends StackProps {
  readonly environment: IcoEnvironment;
}

/**
 * In Case of — application stack.
 *
 * Phase 0: intentionally empty. Resources are added in Phase 2, after the deterministic
 * domain core exists and its access patterns are known. Provisioning infrastructure before
 * the queries are known is how a single-table design acquires indexes nothing needs.
 */
export class IcoStack extends Stack {
  constructor(scope: Construct, id: string, props: IcoStackProps) {
    super(scope, id, props);

    assertBannerInvariant(props.environment);

    Tags.of(this).add("Project", "in-case-of");
    Tags.of(this).add("Environment", props.environment.name);
    Tags.of(this).add("ManagedBy", "cdk");
  }
}
