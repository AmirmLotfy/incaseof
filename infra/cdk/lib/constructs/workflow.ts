import { ArnFormat, Duration, Stack } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import type * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as scheduler from "aws-cdk-lib/aws-scheduler";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import { Construct } from "constructs";
import type { IcoEnvironment } from "../environment.js";

export interface WorkflowProps {
  readonly environment: IcoEnvironment;
  readonly nextAction: lambda.IFunction;
  readonly dispatch: lambda.IFunction;
  readonly momentDue: lambda.IFunction;
}

/**
 * Escalation, and the timers that drive it.
 *
 * **Standard** workflows, not Express. Escalation runs for hours, needs durable execution
 * history for the audit timeline, and waits on human callbacks. Express workflows are
 * cheaper and keep no history, which is the wrong trade when the history *is* the product.
 *
 * The machine is a small loop that holds no opinions: ask the domain what happens next,
 * do it or wait for it, ask again. Every decision lives in Python where it can be unit
 * tested in milliseconds; the state machine only sequences and waits.
 *
 * EventBridge Scheduler owns the timers. Not the phone, not WorkManager, not a sleeping
 * Lambda, and not a Step Functions Wait inside an execution that was already killed — a
 * device-owned timer does not fire when the device is off, which is precisely the case
 * this product exists for.
 */
export class Workflow extends Construct {
  readonly stateMachine: sfn.StateMachine;
  readonly scheduleGroup: scheduler.CfnScheduleGroup;
  readonly schedulerRole: iam.Role;

  constructor(scope: Construct, id: string, props: WorkflowProps) {
    super(scope, id);

    // Every task retries. Transient AWS errors are normal; a retry that contacts somebody
    // twice is not, which is why the handlers are idempotent rather than the retries timid.
    const retry = {
      errors: ["States.TaskFailed", "Lambda.ServiceException", "Lambda.TooManyRequestsException"],
      interval: Duration.seconds(2),
      maxAttempts: 3,
      backoffRate: 2,
    };

    const decide = new tasks.LambdaInvoke(this, "NextAction", {
      lambdaFunction: props.nextAction,
      payloadResponseOnly: true,
      comment: "Ask the domain what happens next for this Alert.",
    }).addRetry(retry);

    const dispatch = new tasks.LambdaInvoke(this, "Dispatch", {
      lambdaFunction: props.dispatch,
      payloadResponseOnly: true,
      resultPath: sfn.JsonPath.DISCARD,
      comment: "Queue the due rungs. Sends nothing itself.",
    }).addRetry(retry);

    const wait = new sfn.Wait(this, "WaitForNextRung", {
      time: sfn.WaitTime.secondsPath("$.seconds"),
      comment: "Sleep until the next rung is due, or until the checking lease expires.",
    });

    const done = new sfn.Succeed(this, "Closed", {
      comment: "Resolved, cancelled, or every rung exhausted.",
    });

    // Dispatch loops straight back rather than waiting: the next rung may already be due,
    // and a ladder with two rungs at the same offset must fire both without a pause.
    dispatch.next(decide);
    wait.next(decide);

    decide.next(
      new sfn.Choice(this, "WhatNext")
        .when(sfn.Condition.stringEquals("$.decision", "DISPATCH"), dispatch)
        .when(sfn.Condition.stringEquals("$.decision", "WAIT"), wait)
        .otherwise(done),
    );

    this.stateMachine = new sfn.StateMachine(this, "Escalation", {
      stateMachineType: sfn.StateMachineType.STANDARD,
      definitionBody: sfn.DefinitionBody.fromChainable(decide),
      // An Alert cannot escalate forever. This is a backstop far beyond any real ladder:
      // reaching it means something is wrong, and it should be visible rather than silent.
      timeout: Duration.hours(24),
      tracingEnabled: true,
      logs: {
        destination: new logs.LogGroup(this, "EscalationLogs", {
          retention: logs.RetentionDays.ONE_MONTH,
        }),
        level: sfn.LogLevel.ALL,
        // Execution data carries alert ids, never contact endpoints — those are resolved
        // in the worker and never enter the workflow payload.
        includeExecutionData: true,
      },
    });

    this.scheduleGroup = new scheduler.CfnScheduleGroup(this, "Moments", {
      name: `ico-moments-${props.environment.name}`,
    });

    // Schedules are created at runtime, one per Moment, then deleted once it resolves.
    // They are not declared here: the set of pending Moments is application state, and
    // putting it in a CloudFormation template would make every check-in a deployment.
    this.schedulerRole = new iam.Role(this, "SchedulerRole", {
      assumedBy: new iam.ServicePrincipal("scheduler.amazonaws.com"),
      description: "Assumed by EventBridge Scheduler to announce that a Moment came due.",
    });
    props.momentDue.grantInvoke(this.schedulerRole);
  }

  /**
   * Let a function create and cancel Moment timers.
   *
   * Scoped to this environment's schedule group, and to passing only the scheduler role —
   * `iam:PassRole` unscoped would let any of these functions hand any role to Scheduler,
   * which is a privilege-escalation path rather than a scheduling permission.
   */
  grantManageSchedules(grantee: iam.IGrantable): void {
    const group = this.scheduleGroup.name ?? "";
    Stack.of(this);

    grantee.grantPrincipal.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          "scheduler:CreateSchedule",
          "scheduler:UpdateSchedule",
          "scheduler:DeleteSchedule",
          "scheduler:GetSchedule",
        ],
        resources: [
          Stack.of(this).formatArn({
            service: "scheduler",
            resource: "schedule",
            resourceName: `${group}/*`,
            arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
          }),
        ],
      }),
    );

    grantee.grantPrincipal.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: ["iam:PassRole"],
        resources: [this.schedulerRole.roleArn],
        conditions: {
          StringEquals: { "iam:PassedToService": "scheduler.amazonaws.com" },
        },
      }),
    );
  }
}
