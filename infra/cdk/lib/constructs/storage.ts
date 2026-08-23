import { RemovalPolicy } from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as kms from "aws-cdk-lib/aws-kms";
import { Construct } from "constructs";
import type { IcoEnvironment } from "../environment.js";

export interface StorageProps {
  readonly environment: IcoEnvironment;
}

/**
 * Authoritative state.
 *
 * A single table, keyed so that everything about one Alert — metadata, ownership history,
 * actions, agent decisions, audit trail — shares a partition key. Rendering the Incident
 * Room or the full audit timeline is then one query rather than a fan-out, which matters
 * because those are the two reads that happen while somebody is waiting.
 *
 * The customer-managed key is not ceremony. This table knows who is alone and when, and
 * who their trusted contacts are; a breach is a stalking risk, not merely a privacy one.
 * An owned key means access is auditable in CloudTrail and revocable independently of IAM.
 */
export class Storage extends Construct {
  readonly table: dynamodb.Table;
  readonly key: kms.Key;

  /** Sparse index over outstanding Moments. See services/adapters/keys.py. */
  static readonly MOMENTS_DUE_INDEX = "gsi1-moments-due";

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id);

    const isProduction = props.environment.name === "prod";

    this.key = new kms.Key(this, "Key", {
      description: `In Case of — ${props.environment.name} data at rest`,
      enableKeyRotation: true,
      removalPolicy: isProduction ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
    });

    this.table = new dynamodb.Table(this, "Table", {
      partitionKey: { name: "pk", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "sk", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.key,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      // Demo and dev are disposable; production state is not, and a stack delete must
      // never be the thing that loses somebody's safety plan.
      removalPolicy: isProduction ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
      deletionProtection: isProduction,
    });

    this.table.addGlobalSecondaryIndex({
      indexName: Storage.MOMENTS_DUE_INDEX,
      partitionKey: { name: "gsi1pk", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "gsi1sk", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });
  }
}
