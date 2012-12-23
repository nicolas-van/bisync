#! /usr/bin/python

import argparse
import os
import os.path
import re

BISYNC_FOLDER = ".bisync"

bisync_folder_re = re.compile(r"""^\.bisync\/.*$""")

class Source:
    def walk(self):
        """ Returns an iterator returning tuples in the following format:
        - Path of the file relative to the root folder of the source
        - Size of the file in bytes
        - Time of last modification in unix format
        """
        pass

class FileSystemSource(Source):
    def __init__(self, path):
        self.path = path

    def walk(self):
        for folder in os.walk(self.path):
            for file_ in folder[2]:
                path = os.path.relpath(os.path.join(folder[0], file_), self.path)
                if bisync_folder_re.match(path):
                    continue
                stat = os.stat(os.path.join(self.path, path))
                yield (path, stat.st_size, stat.st_mtime)

class Synchronizer:
    def __init__(self, folders):
        self.folders = folders

    def synchronize(self):
        for x in self.folders:
            self.build_index(x)

    def build_index(self, source):
        for i in source.walk():
            print i
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Synchronize two folders.')
    parser.add_argument('folders', metavar='folders', type=str, nargs='+',
                       help='folders')

    args = parser.parse_args()

    sync = Synchronizer([FileSystemSource(x) for x in args.folders])

    sync.synchronize()

