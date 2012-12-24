#! /usr/bin/python

"""

TODO:
 - implement conflict resolution
 - implement confirmations
 - think again about version merging

"""

import argparse
import os
import os.path
import re
import json
import shutil

BISYNC_FOLDER = ".bisync"
BISYNC_INDEX = os.path.join(BISYNC_FOLDER, "index")
BISYNC_SUFFIX = "~bisync"

bisync_exclude_re = re.compile(r"""(^\.bisync\/.*$)|(^.*\~bisync$)""")

class Source:
    def walk(self):
        """ Returns an iterator returning tuples in the following format:
        - Path of the file relative to the root folder of the source
        - Size of the file in bytes (integer)
        - Time of last modification in unix format (integer)
        """
        pass

    def exists(self, path):
        """ Returns True if the file exists. """
        pass

    def read_memory(self, path):
        """ Returns the content of the file in a string. """
        pass

    def write_memory(self, path, content):
        """ Write content (as a string) to a file. If the file is contained in a folder or subfolder,
        all those folders must be implicitly created. """
        pass

    def copy_to(self, local_file, dest_file):
        """ Copy a local file (can be accessed using the filesystem) to a file on the source.
        If the file is contained in a folder or subfolder, all those folders must be implicitly created.
        The last modification time of the destination file should be set to the same of the one
        in the local file.
        """
        pass

    def rename(self, from_, to):
        """ Rename a file. If the destination file exists, overwrite it."""
        pass

    def delete(self, path):
        """ Delete a file. If the file does not exists, this method should do nothing.
        After file has been deleted, if the containing folder is empty, the folder should be removed."""
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

    def copy_to(self, local_file, dest_file):
        self._ensure_dir(os.path.join(self.path, dest_file))
        shutil.copy(local_file, os.path.join(self.path, dest_file))
        stat = os.stat(local_file)
        os.utime(os.path.join(self.path, dest_file), (stat.st_atime, stat.st_mtime))

    def rename(self, from_, to):
        self.delete(to)
        shutil.move(os.path.join(self.path, from_), os.path.join(self.path, to))

    def delete(self, path):
        if os.path.exists(os.path.join(self.path, path)):
            os.remove(os.path.join(self.path, path))
        try:
            os.removedirs(os.path.dirname(os.path.joind(self.path, path)))
        except:
            pass # do nothing

    def get_local_name(self, path):
        return os.path.join(self.path, path)

class FileSystemSimulationSource(FileSystemSource):
    def write_memory(self, path, content):
        pass

    def copy_to(self, local_file, dest_file):
        print "Copy %s to %s" % (local_file,
            os.path.join(self.path, dest_file[0:- len(BISYNC_SUFFIX)]))

    def rename(self, from_, to):
        pass

    def delete(self, path):
        print "Delete %s" % os.path.join(self.path, path)


class Synchronizer:
    def synchronize_all(self, folders):
        for x in folders:
            self.build_index(x)
        for i in xrange(len(folders)):
            for j in xrange(i, len(folders)):
                self.sync(folders[i], folders[j])
                self.sync(folders[j], folders[i])
        for x in folders:
            self.save_index(x)

    def sync(self, f1, f2):
        for file_ in f1.index:
            if file_ not in f2.index: # file unknown to f2
                self.transfer(f1, f2, file_)
            else:
                versions1 = f1.index[file_]
                versions2 = f2.index[file_]

                if versions1[-1] == versions2[-1]: # files are the same, nothing to transfer
                    self.merge_versions(f1, f2, file_)
                    continue

                # need to find last revision in common
                i = len(versions1) - 1
                j = len(versions2) - 1
                while j >= 0:
                    if versions1[i] == versions2[j]:
                        break
                    i -= 1
                    if i == -1:
                        i = len(versions1) - 1
                        j -= 1

                if i == len(versions1) - 1: # file in f1 is older
                    self.transfer(f2, f1, file_)
                elif j == len(versions2) - 1: # file in f2 is older
                    self.transfer(f1, f2, file_)
                else: # conflict
                    result = self.resolve_conflict(f1, f2, file_)
                    if result == 1:
                        self.transfer(f1, f2, file_)
                    else:
                        self.transfer(f2, f1, file_)

    def transfer(self, source_from, source_to, path):
        versions1 = source_from.index[path]
        versions2 = source_to.index.get(path, [])
        if versions1[-1][0] == False: # file to delete
            if len(versions2) != 0 and versions2[-1][0] == True:
                source_to.delete(path)
        else: # file to copy
            tmp = path + BISYNC_SUFFIX
            source_to.copy_to(source_from.get_local_name(path), tmp)
            source_to.rename(tmp, path)

        self.merge_versions(source_from, source_to, path)

    def merge_versions(self, source_from, source_to, path):
        # in case of conflict, versions on top of source_from
        # will appear on top of the resulting list
        versions1 = source_from.index[path]
        versions2 = source_to.index.get(path, [])
        last_common_i = -1
        last_common_j = -1
        i = 0
        j = 0
        n_versions = []
        while j < len(versions2):
            if versions1[i] == versions2[j]:
                n_versions += versions2[last_common_j + 1:j]
                n_versions += versions1[last_common_i + 1:i]
                n_versions.append(versions1[i])
                last_common_i = i
                last_common_j = j
                i += 1
                j += 1
                continue
            i += 1
            if i == len(versions1):
                i = last_common_i + 1
                j += 1
        n_versions += versions2[last_common_j + 1:]
        n_versions += versions1[last_common_i + 1:]
        source_from.index[path] = n_versions
        source_to.index[path] = [] + n_versions

    def resolve_conflict(self, f1, f2, file_):
        versions1 = f1.index[file_]
        versions2 = f2.index[file_]
        if versions1[-1][0] == False:
            return 2
        elif versions2[-1][0] == False:
            return 1
        elif versions1[-1][2] > versions2[-1][2]:
            return 1
        else:
            return 2

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

        self.save_index(source)

    def save_index(self, source):
        json_ = json.dumps(source.index)
        source.write_memory(BISYNC_INDEX + BISYNC_SUFFIX, json_)
        source.rename(BISYNC_INDEX + BISYNC_SUFFIX, BISYNC_INDEX)

    def build_current_index(self, source):
        index = {}
        for i in source.walk():
            if not bisync_exclude_re.match(i[0]):
                index[i[0]] = i[1:]
        return index
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Synchronize two folders.')
    parser.add_argument('folders', metavar='folders', type=str, nargs='+',
                       help='folders')
    parser.add_argument("--simulation", help="Only output operations", action="store_true")

    args = parser.parse_args()

    sync = Synchronizer()

    if not args.simulation:
        sources = [FileSystemSource(x) for x in args.folders]
    else:
        sources = [FileSystemSimulationSource(x) for x in args.folders]
    sync.synchronize_all(sources)

