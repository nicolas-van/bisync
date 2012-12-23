#! /usr/bin/python

import argparse
import os
import os.path
import re
import json

BISYNC_FOLDER = ".bisync"
BISYNC_INDEX = os.path.join(BISYNC_FOLDER, "index")

bisync_folder_re = re.compile(r"""^\.bisync\/.*$""")

class Source:
    def walk(self):
        """ Returns an iterator returning tuples in the following format:
        - Path of the file relative to the root folder of the source
        - Size of the file in bytes (integer)
        - Time of last modification in unix format (integer)
        """
        pass

class FileSystemSource(Source):
    def __init__(self, path):
        self.path = path

    def walk(self):
        for folder in os.walk(self.path):
            for file_ in folder[2]:
                path = os.path.relpath(os.path.join(folder[0], file_), self.path)
                stat = os.stat(os.path.join(self.path, path))
                yield [path, stat.st_size, int(stat.st_mtime)]

    def exists(self, path):
        return os.path.exists(os.path.join(self.path, path))

    def read_memory(self, path):
        with open(os.path.join(self.path, path), "r") as file_:
            return file_.read()

    def write_memory(self, path, content):
        self._ensure_dir(os.path.join(self.path, path))
        with open(os.path.join(self.path, path), "w") as file_:
            return file_.write(content)

    def _ensure_dir(self, path):
        dir_ = os.path.dirname(path)
        if not os.path.exists(dir_):
            os.makedirs(dir_)


class Synchronizer:
    def __init__(self, folders):
        self.folders = folders

    def synchronize(self):
        for x in self.folders:
            self.build_index(x)

    def build_index(self, source):
        c_index = self.build_current_index(source)
        p_index = {}
        if source.exists(BISYNC_INDEX):
            content = source.read_memory(BISYNC_INDEX)
            p_index = json.loads(content)
                    
        for file_ in p_index.keys():
            if file_ not in c_index and p_index[file_][-1][0] == True: # file was deleted
                p_index[file_].append([False])

        for file_ in c_index.keys():
            if file_ not in p_index: # new file
                p_index[file_] = [[True] + c_index[file_]]
            else:
                last = p_index[file_][-1]
                if last[1:] != c_index[file_]: # file was modified or re-created
                    p_index[file_].append([True] + c_index[file_])

        source.index = p_index

        json_ = json.dumps(p_index)
        print json_
        source.write_memory(BISYNC_INDEX, json_)

    def build_current_index(self, source):
        index = {}
        for i in source.walk():
            if not bisync_folder_re.match(i[0]):
                index[i[0]] = i[1:]
        return index
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Synchronize two folders.')
    parser.add_argument('folders', metavar='folders', type=str, nargs='+',
                       help='folders')

    args = parser.parse_args()

    sync = Synchronizer([FileSystemSource(x) for x in args.folders])

    sync.synchronize()

