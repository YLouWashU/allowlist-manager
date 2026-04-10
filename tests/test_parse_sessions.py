import sys, os, json, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.parse_sessions import split_command, extract_executable, categorize, parse_sessions, classify_executables


class TestSplitCommand(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(split_command('git status'), ['git status'])

    def test_and_and(self):
        parts = split_command('cd foo && git status')
        self.assertEqual(parts, ['cd foo', 'git status'])

    def test_pipe(self):
        parts = split_command('ls | grep foo')
        self.assertEqual(parts, ['ls', 'grep foo'])

    def test_semicolon(self):
        parts = split_command('echo hi; echo bye')
        self.assertEqual(parts, ['echo hi', 'echo bye'])

    def test_or(self):
        parts = split_command('git pull || echo failed')
        self.assertEqual(parts, ['git pull', 'echo failed'])


class TestExtractExecutable(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(extract_executable('git status'), 'git')

    def test_venv_path(self):
        self.assertEqual(extract_executable('.venv/bin/pytest tests/'), '.venv/bin/pytest')

    def test_env_var_prefix(self):
        self.assertEqual(extract_executable('DISPLAY=:0 chromium'), 'chromium')

    def test_empty(self):
        self.assertIsNone(extract_executable(''))

    def test_comment(self):
        self.assertIsNone(extract_executable('# this is a comment'))


class TestCategorize(unittest.TestCase):
    def test_vcs(self):
        self.assertEqual(categorize('git'), 'vcs')

    def test_runtime(self):
        self.assertEqual(categorize('python3'), 'runtime')

    def test_package_manager(self):
        self.assertEqual(categorize('npm'), 'package_manager')

    def test_project_specific(self):
        self.assertEqual(categorize('.venv/bin/pytest'), 'project_specific')

    def test_other(self):
        self.assertEqual(categorize('sometool'), 'other')


class TestParseSessions(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        session = [
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"name": "Bash", "input": {"command": "git status && npm install"}}
            ]}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"name": "Bash", "input": {"command": "git status"}}
            ]}},
            {"type": "user", "message": {"role": "user", "content": "ok"}},
        ]
        self.session_file = Path(self.tmpdir) / 'test.jsonl'
        with open(self.session_file, 'w') as f:
            for obj in session:
                f.write(json.dumps(obj) + '\n')

    def test_counts(self):
        counts = parse_sessions(files=[self.session_file])
        self.assertEqual(counts.get('git'), 2)
        self.assertEqual(counts.get('npm'), 1)


class TestClassifyExecutables(unittest.TestCase):
    def test_classification(self):
        counts = {'git': 5, 'sudo': 2, 'newcmd': 1}
        allow_list = ['Bash(git *)']
        result = classify_executables(counts, allow_list)
        self.assertEqual(len(result['covered']), 1)
        self.assertEqual(result['covered'][0]['executable'], 'git')
        self.assertEqual(len(result['dangerous_gap']), 1)
        self.assertEqual(result['dangerous_gap'][0]['executable'], 'sudo')
        self.assertEqual(len(result['safe_gap']), 1)
        self.assertEqual(result['safe_gap'][0]['executable'], 'newcmd')


if __name__ == '__main__':
    unittest.main()
