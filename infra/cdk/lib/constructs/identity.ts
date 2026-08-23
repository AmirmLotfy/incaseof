import { Duration, RemovalPolicy } from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import { Construct } from "constructs";
import type { IcoEnvironment } from "../environment.js";

export interface IdentityProps {
  readonly environment: IcoEnvironment;
}

/**
 * Who the subject is.
 *
 * Deliberately plain. Authentication is not where this product is interesting, and the
 * build contract is explicit that hackathon success must not depend on elaborate auth.
 *
 * Note what is *not* here: responders never get an account. They act through a signed,
 * single-Alert token instead, because requiring a friend to sign up at 2am in order to
 * say "I've got her" would defeat the point.
 */
export class Identity extends Construct {
  readonly userPool: cognito.UserPool;
  readonly client: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: IdentityProps) {
    super(scope, id);

    const isProduction = props.environment.name === "prod";

    this.userPool = new cognito.UserPool(this, "UserPool", {
      selfSignUpEnabled: true,
      signInAliases: { email: true, phone: true },
      autoVerify: { email: true },
      standardAttributes: {
        phoneNumber: { required: false, mutable: true },
        timezone: { required: false, mutable: true },
      },
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      mfa: cognito.Mfa.OPTIONAL,
      mfaSecondFactor: { sms: true, otp: true },
      // ESSENTIALS, not PLUS. Threat protection (the successor to the deprecated
      // advancedSecurityMode) requires the PLUS plan and bills per monthly active user.
      // On a $50 hackathon credit that is a deliberate decision rather than a default —
      // and it is the first thing to turn on for real users, since this account holds who
      // is alone and when.
      featurePlan: cognito.FeaturePlan.ESSENTIALS,
      removalPolicy: isProduction ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
    });

    this.client = this.userPool.addClient("AndroidClient", {
      authFlows: { userSrp: true },
      // No client secret: the app ships to devices and cannot keep one.
      generateSecret: false,
      // The app authenticates with SRP and never uses a hosted-UI redirect, so the
      // OAuth flows are switched off entirely. Left at CDK's defaults they enable the
      // *implicit* flow, which returns tokens in a URL fragment where they leak through
      // history and referrers, and they register a placeholder callback of
      // https://example.com — a domain nobody here controls.
      disableOAuth: true,
      accessTokenValidity: Duration.hours(1),
      idTokenValidity: Duration.hours(1),
      refreshTokenValidity: Duration.days(30),
      preventUserExistenceErrors: true,
    });
  }
}
