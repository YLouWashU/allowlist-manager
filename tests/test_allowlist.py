import sys, os, json, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.allowlist import pattern_covers, is_covered, add_pattern, add_deny_pattern, load_settings, save_settings, normalize_executable


class TestNormalizeExecutable(unittest.TestCase):
    def test_dot_venv(self):
        self.assertEqual(normalize_executable(".venv/bin/python"), "*venv/bin/python")

    def test_plain_venv(self):
        self.assertEqual(normalize_executable("venv/bin/pip"), "*venv/bin/pip")

    def test_absolute_venv(self):
        self.assertEqual(
            normalize_executable("/home/user/proj/.venv/bin/pytest"),
            "*venv/bin/pytest"
        )

    def test_absolute_plain_venv(self):
        self.assertEqual(
            normalize_executable("/home/user/Code/ScoreAnalysis/venv/bin/python"),
            "*venv/bin/python"
        )

    def test_non_venv(self):
        self.assertEqual(normalize_executable("python3"), "python3")
        self.assertEqual(normalize_executable("git"), "git")
        self.assertEqual(normalize_executable("/usr/bin/env"), "/usr/bin/env")


class TestPatternCovers(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(pattern_covers("Bash(git *)", "git"))

    def test_prefix_match(self):
        self.assertTrue(pattern_covers("Bash(.venv/bin/python *)", ".venv/bin/python"))

    def test_no_match(self):
        self.assertFalse(pattern_covers("Bash(git *)", "npm"))

    def test_partial_no_match(self):
        self.assertFalse(pattern_covers("Bash(git *)", "gits"))

    def test_non_bash_pattern(self):
        self.assertFalse(pattern_covers("Read(*)", "git"))

    def test_wildcard_prefix_dot_venv(self):
        self.assertTrue(pattern_covers("Bash(*venv/bin/python *)", ".venv/bin/python"))

    def test_wildcard_prefix_plain_venv(self):
        self.assertTrue(pattern_covers("Bash(*venv/bin/python *)", "venv/bin/python"))

    def test_wildcard_prefix_absolute(self):
        self.assertTrue(
            pattern_covers("Bash(*venv/bin/python *)", "/home/user/proj/.venv/bin/python")
        )

    def test_wildcard_prefix_no_match(self):
        self.assertFalse(pattern_covers("Bash(*venv/bin/python *)", "python3"))

    def test_wildcard_prefix_no_cross_match(self):
        self.assertFalse(pattern_covers("Bash(*venv/bin/python *)", ".venv/bin/python3"))


class TestIsCovered(unittest.TestCase):
    def test_covered(self):
        allow = ["Bash(git *)", "Bash(npm *)"]
        self.assertTrue(is_covered("git", allow))
        self.assertTrue(is_covered("npm", allow))

    def test_not_covered(self):
        allow = ["Bash(git *)"]
        self.assertFalse(is_covered("yarn", allow))

    def test_empty_list(self):
        self.assertFalse(is_covered("git", []))

    def test_venv_covered_by_wildcard(self):
        allow = ["Bash(*venv/bin/python *)"]
        self.assertTrue(is_covered(".venv/bin/python", allow))
        self.assertTrue(is_covered("venv/bin/python", allow))
        self.assertTrue(is_covered("/home/user/proj/.venv/bin/python", allow))

    def test_venv_not_covered_by_different_wildcard(self):
        allow = ["Bash(*venv/bin/python *)"]
        self.assertFalse(is_covered(".venv/bin/pip", allow))


class TestAddPattern(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        import lib.allowlist as a
        self._orig_settings = a.SETTINGS_FILE
        self._orig_lock_dir = a.LOCK_DIR
        a.SETTINGS_FILE = Path(self.tmpdir) / "settings.json"
        a.LOCK_DIR = Path(self.tmpdir)
        base = {"permissions": {"allow": ["Bash(git *)"], "deny": []}}
        with open(a.SETTINGS_FILE, "w") as f:
            json.dump(base, f)

    def tearDown(self):
        import lib.allowlist as a
        a.SETTINGS_FILE = self._orig_settings
        a.LOCK_DIR = self._orig_lock_dir

    def test_add_new_pattern(self):
        add_pattern("npm")
        settings = load_settings()
        self.assertIn("Bash(npm *)", settings["permissions"]["allow"])

    def test_no_duplicate(self):
        add_pattern("git")
        settings = load_settings()
        count = settings["permissions"]["allow"].count("Bash(git *)")
        self.assertEqual(count, 1)

    def test_add_deny(self):
        add_deny_pattern("rm")
        settings = load_settings()
        self.assertIn("Bash(rm *)", settings["permissions"]["deny"])

    def test_venv_path_expands_to_wildcard(self):
        add_pattern(".venv/bin/pytest")
        settings = load_settings()
        self.assertIn("Bash(*venv/bin/pytest *)", settings["permissions"]["allow"])
        self.assertNotIn("Bash(.venv/bin/pytest *)", settings["permissions"]["allow"])

    def test_venv_absolute_path_expands_to_wildcard(self):
        add_pattern("/home/user/proj/.venv/bin/mylib")
        settings = load_settings()
        self.assertIn("Bash(*venv/bin/mylib *)", settings["permissions"]["allow"])

    def test_venv_no_duplicate_after_expansion(self):
        add_pattern(".venv/bin/pytest")
        add_pattern("venv/bin/pytest")
        settings = load_settings()
        count = settings["permissions"]["allow"].count("Bash(*venv/bin/pytest *)")
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
