// Shared configuration of the toolkit for the Node scripts (same rules as kitconfig.py).
// Reads /PATH/TO/WORKDIR/config.json; the env var ALV_<KEY> wins over the file.
import { existsSync, readFileSync } from "node:fs";

export const WORKDIR = "/PATH/TO/WORKDIR";
const CONFIG_PATH = `${WORKDIR}/config.json`;
if (!existsSync(CONFIG_PATH)) {
  console.error(`missing ${CONFIG_PATH}: copy config.example.json to config.json and edit it`);
  process.exit(1);
}
const CONFIG = JSON.parse(readFileSync(CONFIG_PATH, "utf8"));

export function cfg(key) {
  const env = process.env[`ALV_${key.toUpperCase()}`];
  const current = CONFIG[key];
  if (env !== undefined) {
    if (typeof current === "object" && current !== null) return JSON.parse(env);
    if (typeof current === "number") return Number(env);
    return env;
  }
  if (!(key in CONFIG)) throw new Error(`missing config key '${key}' (see config.example.json)`);
  return current;
}

// Chromium for Playwright: the configured binary, or undefined so playwright-core uses the one
// installed with `npx playwright@1.48.2 install chromium`.
export function chromiumPath() {
  return cfg("chromium_path") || undefined;
}
