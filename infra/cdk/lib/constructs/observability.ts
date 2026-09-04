import { Duration } from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import type * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import type * as sfn from "aws-cdk-lib/aws-stepfunctions";
import type * as sqs from "aws-cdk-lib/aws-sqs";
import { Construct } from "constructs";
import type { IcoEnvironment } from "../environment.js";

export interface ObservabilityProps {
  readonly environment: IcoEnvironment;
  readonly api: lambda.IFunction;
  readonly functions: lambda.IFunction[];
  readonly stateMachine: sfn.IStateMachine;
  readonly actionDlq: sqs.IQueue;
  readonly scheduleGroupName: string;
  readonly agentCoreLogs: logs.ILogGroup;
}

/** Judge-visible service health without recording plan text or contact endpoints. */
export class Observability extends Construct {
  constructor(scope: Construct, id: string, props: ObservabilityProps) {
    super(scope, id);
    const minute = Duration.minutes(1);
    const alarmDefaults = {
      evaluationPeriods: 3,
      datapointsToAlarm: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    };

    const apiErrorRate = new cloudwatch.Alarm(this, "ApiErrorRate", {
      metric: new cloudwatch.MathExpression({
        expression: "IF(invocations > 0, errors * 100 / invocations, 0)",
        period: minute,
        usingMetrics: {
          errors: props.api.metricErrors({ period: minute }),
          invocations: props.api.metricInvocations({ period: minute }),
        },
      }),
      threshold: 5,
      ...alarmDefaults,
    });
    const apiLatency = new cloudwatch.Alarm(this, "ApiLatencyP99", {
      metric: props.api.metricDuration({ statistic: "p99", period: minute }),
      threshold: 5000,
      ...alarmDefaults,
    });
    const lambdaErrors = new cloudwatch.Alarm(this, "LambdaErrors", {
      metric: new cloudwatch.MathExpression({
        expression: props.functions.map((_, index) => `m${index}`).join("+") || "0",
        period: minute,
        usingMetrics: Object.fromEntries(
          props.functions.map((fn, index) => [`m${index}`, fn.metricErrors({ period: minute })]),
        ),
      }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      ...alarmDefaults,
    });
    const workflowFailures = new cloudwatch.Alarm(this, "WorkflowFailures", {
      metric: new cloudwatch.MathExpression({
        expression: "failed+timedout",
        period: minute,
        usingMetrics: {
          failed: props.stateMachine.metricFailed({ period: minute }),
          timedout: props.stateMachine.metricTimedOut({ period: minute }),
        },
      }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      ...alarmDefaults,
    });
    const dlqDepth = new cloudwatch.Alarm(this, "ActionDlqDepth", {
      metric: props.actionDlq.metricApproximateNumberOfMessagesVisible({ period: minute }),
      threshold: 1,
      evaluationPeriods: 1,
      datapointsToAlarm: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    const schedulerErrors = new cloudwatch.Alarm(this, "SchedulerTargetErrors", {
      metric: new cloudwatch.Metric({
        namespace: "AWS/Scheduler",
        metricName: "TargetErrorCount",
        dimensionsMap: { ScheduleGroup: props.scheduleGroupName },
        statistic: "Sum",
        period: minute,
      }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      ...alarmDefaults,
    });

    const agentFailures = new logs.MetricFilter(this, "AgentCoreFailureMetric", {
      logGroup: props.agentCoreLogs,
      filterPattern: logs.FilterPattern.anyTerm("ERROR", "Exception", "Traceback"),
      metricNamespace: "InCaseOf/AgentCore",
      metricName: "Failures",
      metricValue: "1",
      defaultValue: 0,
    });
    const agentLatency = new logs.MetricFilter(this, "AgentCoreLatencyMetric", {
      logGroup: props.agentCoreLogs,
      filterPattern: logs.FilterPattern.stringValue("$.event", "=", "compile_completed"),
      metricNamespace: "InCaseOf/AgentCore",
      metricName: "CompileLatencyMs",
      metricValue: "$.latency_ms",
    });
    const agentFailuresAlarm = new cloudwatch.Alarm(this, "AgentCoreFailures", {
      metric: agentFailures.metric({ statistic: "Sum", period: minute }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      ...alarmDefaults,
    });
    const agentLatencyAlarm = new cloudwatch.Alarm(this, "AgentCoreLatencyP99", {
      metric: agentLatency.metric({ statistic: "p99", period: minute }),
      threshold: 12000,
      ...alarmDefaults,
    });

    const dashboard = new cloudwatch.Dashboard(this, "Dashboard", {
      dashboardName: `ico-${props.environment.name}-health`,
      start: "-PT8H",
      periodOverride: cloudwatch.PeriodOverride.INHERIT,
    });
    dashboard.addWidgets(
      new cloudwatch.TextWidget({
        width: 24,
        height: 2,
        markdown: `# ICO ${props.environment.name} health\nNo private plan text, tokens, or contact endpoints are emitted as metrics.`,
      }),
      new cloudwatch.AlarmWidget({ width: 12, title: "API", alarm: apiErrorRate }),
      new cloudwatch.AlarmWidget({ width: 12, title: "AgentCore", alarm: agentFailuresAlarm }),
      new cloudwatch.AlarmStatusWidget({
        width: 24,
        title: "Operational gates",
        alarms: [apiLatency, lambdaErrors, workflowFailures, dlqDepth, schedulerErrors, agentLatencyAlarm],
      }),
      new cloudwatch.GraphWidget({
        width: 12,
        title: "API latency p99",
        left: [props.api.metricDuration({ statistic: "p99", period: minute })],
      }),
      new cloudwatch.GraphWidget({
        width: 12,
        title: "AgentCore compile latency",
        left: [agentLatency.metric({ statistic: "p99", period: minute })],
      }),
    );
  }
}
