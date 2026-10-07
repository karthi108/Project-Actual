// Syntax check with js-yaml already frozen in the frontend dependency tree.
// This does not replace Docker Compose, Collector, Terraform or GitHub validation.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";

const require = createRequire(
  resolve("apps/web/node_modules/.pnpm/js-yaml@4.3.2/node_modules/js-yaml/package.json"),
);
const yaml = require("js-yaml");
for (const path of [
  "deploy/compose.yaml",
  "deploy/otel-collector.yaml",
  "deploy/terraform/cloud-init.yaml",
  ".github/workflows/verify.yml",
]) {
  const value = yaml.load(readFileSync(path, "utf8"));
  if (!value || typeof value !== "object") throw new Error(`Invalid config: ${path}`);
  process.stdout.write(`YAML parsed: ${path}\n`);
}
