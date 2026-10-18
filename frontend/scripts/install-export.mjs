import { cp, access } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const output = fileURLToPath(new URL("../out/", import.meta.url));
const target = fileURLToPath(
  new URL("../../college-console/", import.meta.url),
);
await access(output);
await cp(output, target, { recursive: true, force: true });
console.log(
  "College interface exported to college-console. Start the Python workbench to use it.",
);
