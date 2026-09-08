import type * as kms from "aws-cdk-lib/aws-kms";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";
import type { IcoEnvironment } from "../environment.js";

export interface SecretsProps {
  readonly environment: IcoEnvironment;
  readonly key: kms.IKey;
}

/**
 * Credentials.
 *
 * Created empty and populated out of band. A secret whose value appears in a CDK context
 * value, a template, or a repository is not a secret — and CloudFormation templates are
 * readable by anyone with describe permissions on the stack.
 */
export class Secrets extends Construct {
  readonly responderTokenSigningKey: secretsmanager.Secret;

  constructor(scope: Construct, id: string, props: SecretsProps) {
    super(scope, id);

    this.responderTokenSigningKey = new secretsmanager.Secret(this, "ResponderTokenKey", {
      description:
        "Signs single-Alert responder tokens. Rotating it invalidates every outstanding link.",
      encryptionKey: props.key,
      generateSecretString: {
        passwordLength: 64,
        excludePunctuation: true,
      },
    });
  }
}
