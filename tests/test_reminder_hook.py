import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "node is required for the reminder hook")
class ReminderHookTest(unittest.TestCase):
    """UserPromptSubmit hook that re-adds the short rules reminder every prompt."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        base = Path(self.temp_dir.name)
        self.plugin_root = base / "plugin with spaces"
        shutil.copytree(ROOT / "hooks", self.plugin_root / "hooks")
        self.config_dir = base / "claude config"
        self.config_dir.mkdir()
        self.tmp = base / "tmp"
        self.tmp.mkdir()

    def opt_in(self):
        (self.config_dir / ".i-have-adhd-always").touch()

    def prompt(self, text, session="s1"):
        config = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        hook = config["hooks"]["UserPromptSubmit"][0]["hooks"][0]
        env = os.environ.copy()
        env.update(
            CLAUDE_CONFIG_DIR=str(self.config_dir),
            CLAUDE_PLUGIN_ROOT=str(self.plugin_root),
            PLUGIN_ROOT=str(self.plugin_root),
            TMPDIR=str(self.tmp),
            TEMP=str(self.tmp),
            TMP=str(self.tmp),
        )
        result = subprocess.run(
            hook["command"],
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            env=env,
            input=json.dumps(
                {"session_id": session, "hook_event_name": "UserPromptSubmit", "prompt": text}
            ),
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        return result.stdout

    def test_silent_without_opt_in_flag(self):
        self.assertEqual("", self.prompt("fix the bug"))

    def test_injects_reminder_every_prompt_when_opted_in(self):
        self.opt_in()
        for _ in range(2):
            self.assertIn("ADHD MODE still active", self.prompt("fix the bug"))

    def test_stop_silences_only_that_session_until_restarted(self):
        self.opt_in()
        self.assertEqual("", self.prompt("ok, stop adhd mode please"))
        self.assertEqual("", self.prompt("next question"))
        self.assertIn("ADHD MODE", self.prompt("next question", session="other"))
        self.assertIn("ADHD MODE", self.prompt("start adhd mode"))
        self.assertIn("ADHD MODE", self.prompt("next question"))

    def test_normal_mode_also_silences(self):
        self.opt_in()
        self.assertEqual("", self.prompt("Normal mode"))
        self.assertEqual("", self.prompt("hello"))

    def test_bad_stdin_still_exits_cleanly(self):
        self.opt_in()
        config = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        hook = config["hooks"]["UserPromptSubmit"][0]["hooks"][0]
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.config_dir),
                   CLAUDE_PLUGIN_ROOT=str(self.plugin_root), TMPDIR=str(self.tmp))
        result = subprocess.run(hook["command"], shell=True, capture_output=True,
                                text=True, env=env, input="not json")
        self.assertEqual(0, result.returncode)
        self.assertIn("ADHD MODE", result.stdout)


if __name__ == "__main__":
    unittest.main()
