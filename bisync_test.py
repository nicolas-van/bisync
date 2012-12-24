import bisync
import json
import unittest

class TestSource(bisync.Source):
    def __init__(self, index):
        self.test_index = index
        self.nbr_copy = 0
        self.nbr_delete = 0

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
        self.nbr_copy += 1

    def rename(self, from_, to):
        pass

    def delete(self, path):
        self.nbr_delete += 1

    def get_local_name(self, path):
        return path

class TestSequenceFunctions(unittest.TestCase):

    def test_first_sync(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"]],
        })
        s2 = TestSource({
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 0)
        self.assertEqual(s2.nbr_copy, 1)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 0)

    def test_updated_version(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"], [True, "1", "2"]],
        })
        s2 = TestSource({
            "file1": [[True, "1", "1"]],
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"], [True, "1", "2"]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 0)
        self.assertEqual(s2.nbr_copy, 1)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 0)

    def test_deleted_file(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"], [False]],
        })
        s2 = TestSource({
            "file1": [[True, "1", "1"]],
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"], [False]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 0)
        self.assertEqual(s2.nbr_copy, 0)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 1)

    def test_recreated_file(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"], [False]],
        })
        s2 = TestSource({
            "file1": [[True, "1", "1"], [False], [True, "1", "4"]],
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"], [False], [True, "1", "4"]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 1)
        self.assertEqual(s2.nbr_copy, 0)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 0)

    def test_moved_file(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"], [False]],
            "file2": [[True, "1", "1"]],
        })
        s2 = TestSource({
            "file1": [[True, "1", "1"]],
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"], [False]],
            "file2": [[True, "1", "1"]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 0)
        self.assertEqual(s2.nbr_copy, 1)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 1)

    def test_conflict(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"], [True, "1", "3"]],
        })
        s2 = TestSource({
            "file1": [[True, "1", "1"], [True, "1", "2"]],
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"], [True, "1", "2"], [True, "1", "3"]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 0)
        self.assertEqual(s2.nbr_copy, 1)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 0)

    def test_conflict_one_delete(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"], [True, "1", "3"], [False]],
        })
        s2 = TestSource({
            "file1": [[True, "1", "1"], [True, "1", "2"]],
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"], [True, "1", "3"], [False], [True, "1", "2"]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 1)
        self.assertEqual(s2.nbr_copy, 0)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 0)

    def test_conflict_two_delete(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"], [True, "1", "3"], [False]],
        })
        s2 = TestSource({
            "file1": [[True, "1", "1"], [True, "1", "2"], [False]],
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"], [True, "1", "2"], [True, "1", "3"], [False]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 0)
        self.assertEqual(s2.nbr_copy, 0)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 0)

    def test_external_copy(self):
        s1 = TestSource({
            "file1": [[True, "1", "1"], [True, "1", "2"]],
        })
        s2 = TestSource({
            "file1": [[True, "1", "2"]],
        })
        sync = bisync.Synchronizer(no_trash=True)
        sync.synchronize_all([s1, s2])
        result = {
            "file1": [[True, "1", "1"], [True, "1", "2"]],
        }
        self.assertEqual(s1.index, result)
        self.assertEqual(s1.nbr_copy, 0)
        self.assertEqual(s2.nbr_copy, 0)
        self.assertEqual(s1.nbr_delete, 0)
        self.assertEqual(s2.nbr_delete, 0)

if __name__ == '__main__':
    unittest.main()