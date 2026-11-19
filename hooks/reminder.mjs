// UserPromptSubmit hook: re-adds a short reminder of the i-have-adhd rules
// before every prompt, so they do not fade in long sessions. The full ruleset
// still comes from the SessionStart hook (always-on.mjs); this only keeps it
// fresh. Opt-in is the same flag: $CLAUDE_CONFIG_DIR/.i-have-adhd-always.
//
// "stop adhd mode" / "normal mode" silences the reminder for the rest of that
// session; "start adhd mode" or "/i-have-adhd" turns it back on. Per-session
// state lives in a marker file under the OS temp dir, keyed by session_id.
// Never blocks the prompt: any failure exits 0 with no output.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const REMINDER =
  "ADHD MODE still active (i-have-adhd reminder). This reply must: " +
  "1) lead with the next action; 2) number multi-step work, fewest steps; " +
  "3) end with ONE concrete next action; 4) skip tangents, offer them after; " +
  "5) restate where we are (step X of Y); 6) give concrete time estimates; " +
  "7) show what now works; 8) errors = cause + fix, no drama; " +
  "9) max 5 items per group; 10) no preamble, recap or closing pleasantries. " +
  '"stop adhd mode" turns this off for the session.';

const OFF = /\b(stop adhd mode|normal mode)\b/i;
const ON = /\bstart adhd mode\b|\/i-have-adhd\b/i;

try {
  const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude");
  if (!fs.existsSync(path.join(claudeDir, ".i-have-adhd-always"))) process.exit(0);

  let input = {};
  try {
    input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
  } catch {}
  const prompt = typeof input.prompt === "string" ? input.prompt : "";
  const session = String(input.session_id || "no-session").replace(/[^A-Za-z0-9_-]/g, "_");
  const markerDir = path.join(os.tmpdir(), "i-have-adhd-off");
  const marker = path.join(markerDir, session);

  if (OFF.test(prompt)) {
    fs.mkdirSync(markerDir, { recursive: true });
    fs.writeFileSync(marker, "");
    process.exit(0);
  }
  if (ON.test(prompt)) fs.rmSync(marker, { force: true });
  if (fs.existsSync(marker)) process.exit(0);

  process.stdout.write(REMINDER + "\n");
} catch {
  process.exit(0);
}
