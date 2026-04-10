import sys, os, json, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.dangerous import is_dangerous, append_to_queue, read_queue, write_queue


class TestIsDangerous(unittest.TestCase):
    def test_bare_dangerous(self):
        self.assertTrue(is_dangerous('rm'))
        self.assertTrue(is_dangerous('sudo'))
        self.assertTrue(is_dangerous('dd'))

    def test_safe(self):
        self.assertFalse(is_dangerous('git'))
        self.assertFalse(is_dangerous('python3'))
        self.assertFalse(is_dangerous('npm'))

    def test_path_with_dangerous_name(self):
        self.assertTrue(is_dangerous('/usr/bin/rm'))
        self.assertTrue(is_dangerous('/usr/local/bin/sudo'))

    def test_path_with_safe_name(self):
        self.assertFalse(is_dangerous('/usr/bin/git'))


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        import lib.dangerous as d
        self._orig_queue = d.QUEUE_FILE
        self._orig_dir = d.QUEUE_DIR
        from pathlib import Path
        d.QUEUE_DIR = Path(self.tmpdir)
        d.QUEUE_FILE = Path(self.tmpdir) / 'skipped.jsonl'

    def tearDown(self):
        import lib.dangerous as d
        d.QUEUE_FILE = self._orig_queue
        d.QUEUE_DIR = self._orig_dir

    def test_append_and_read(self):
        append_to_queue('sudo apt install foo', 'sudo', 'sess1')
        entries = read_queue()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['executable'], 'sudo')
        self.assertEqual(entries[0]['command'], 'sudo apt install foo')
        self.assertEqual(entries[0]['session'], 'sess1')
        self.assertIn('timestamp', entries[0])

    def test_write_queue_removes_entries(self):
        append_to_queue('sudo foo', 'sudo', 's1')
        append_to_queue('dd if=/dev/zero', 'dd', 's2')
        entries = read_queue()
        write_queue([entries[1]])  # keep only dd
        remaining = read_queue()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]['executable'], 'dd')

    def test_read_empty(self):
        self.assertEqual(read_queue(), [])


if __name__ == '__main__':
    unittest.main()
