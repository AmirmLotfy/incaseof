import { Duration } from "aws-cdk-lib";
import type * as kms from "aws-cdk-lib/aws-kms";
import * as sqs from "aws-cdk-lib/aws-sqs";
import { Construct } from "constructs";

export interface MessagingProps {
  readonly key: kms.IKey;
}

/**
 * The action outbox.
 *
 * Workflows never call a provider directly. They write an ActionIntent, which reaches a
 * worker through this queue, which calls the provider and records a callback. That
 * indirection is what makes retries predictable and keeps provider latency out of the
 * state machine.
 *
 * Every queue has a dead-letter queue. In this product a silently dropped message is a
 * person who was never contacted, so messages that cannot be processed must end up
 * somewhere a human and an alarm can see them.
 */
export class Messaging extends Construct {
  readonly actionQueue: sqs.Queue;
  readonly actionDlq: sqs.Queue;

  constructor(scope: Construct, id: string, props: MessagingProps) {
    super(scope, id);

    this.actionDlq = new sqs.Queue(this, "ActionDlq", {
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: props.key,
      retentionPeriod: Duration.days(14),
      enforceSSL: true,
    });

    this.actionQueue = new sqs.Queue(this, "ActionQueue", {
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: props.key,
      enforceSSL: true,
      // Long enough for a provider call plus its callback, short enough that a stuck
      // message returns for another attempt while the Alert is still live.
      visibilityTimeout: Duration.seconds(120),
      retentionPeriod: Duration.days(4),
      deadLetterQueue: {
        queue: this.actionDlq,
        // Three attempts: a transient provider failure gets retried, a poison message
        // stops being retried before it delays every other action behind it.
        maxReceiveCount: 3,
      },
    });
  }
}
