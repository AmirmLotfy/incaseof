#!/usr/bin/env node
import { App } from "aws-cdk-lib";
import { ENVIRONMENTS, type EnvName } from "../lib/environment.js";
import { IcoStack } from "../lib/incaseof-stack.js";

const app = new App();

const requested = (app.node.tryGetContext("env") as EnvName | undefined) ?? "dev";
const environment = ENVIRONMENTS[requested];

if (!environment) {
  throw new Error(
    `Unknown environment "${requested}". Expected one of: ${Object.keys(ENVIRONMENTS).join(", ")}`,
  );
}

new IcoStack(app, `IcoStack-${environment.name}`, {
  environment,
  env: { region: environment.region },
  description: "In Case of — someone notices.",
});
