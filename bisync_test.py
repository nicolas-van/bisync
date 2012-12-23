import bisync
import json
import unittest

class TestSource(bisync.Source):
    def __init__(self, index):
        self.test_index = index

    def walk(self):
        for file_ in self.test_index.keys():
            last = self.test_index[file_][-1]
            if last[0] == True:
                yield [file_, last[1], last[2]]

    def exists(self, path):
        if path == bisync.BISYNC_INDEX:
            return True
        elif path in self.text_index:
            return True
        else:
            return False

    def read_memory(self, path):
        return json.dumps(self.test_index)

    def write_memory(self, path, content):
        pass

    def copy_to(self, local_file, dest_file):
        pass

    def rename(self, from_, to):
        pass

    def delete(self, path):
        pass

    def get_local_name(self, path):
        return path

class TestSequenceFunctions(unittest.TestCase):

    def test_first_sync(self):
        s1 = TestSource({
            "file1": ["1", "1"],
        })
        s2 = TestSource({
        })
        sync = bisync.Synchronizer()
        sync.synchronize_all([s1, s2])
        self.assertEqual(s1.test_index, s1.index)
        self.assertEqual(s1.test_index, s2.index)

if __name__ == '__main__':
    unittest.main()