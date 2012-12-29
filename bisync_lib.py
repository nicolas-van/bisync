#! /usr/bin/python

#    Bisync
#    Copyright (C) 2012 Nicolas Vanhoren
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

TODO:
 - add lock ?
 - add ignore ?

"""

import argparse
import os
import os.path
import re
import json
import shutil
import datetime

BISYNC_FOLDER = ".bisync"
BISYNC_INDEX = os.path.join(BISYNC_FOLDER, "index")
BISYNC_SUFFIX = "~bisync"
BISYNC_TRASH = "bisync_trash"

bisync_exclude_re = re.compile(r"""(^\.bisync\/.*$)|(^.*\~bisync$)|(^bisync_trash\/.*$)""")

class Source(object):
    def get_name(self):
        """ Returns the string used to construct the source. """
        pass

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
        """ Rename a file. If the destination file exists, overwrite it. If the destination file is
        in a folder that does not exists, that folder must be implicitly created. """
        pass

    def delete(self, path):
        """ Delete a file. If the file does not exists, this method should do nothing.
        After file has been deleted, if the containing folder is empty, the folder should be removed."""
        pass



class FileSystemSource(Source):
    def __init__(self, path):
        self.path = path

    def get_name(self):
        return self.path

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
        self._ensure_dir(os.path.join(self.path, to))
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

class Synchronizer(object):
    def __init__(self, no_trash=False):
        self.no_trash = no_trash

    def synchronize_all(self, folders):
        for x in folders:
            self.build_index(x)
        for i in xrange(len(folders)):
            for j in xrange(i, len(folders)):
                self.sync(folders[i], folders[j])
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
                    self.merge_versions(f1, f2, file_) # but we merge versions anyway
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

        for file_ in f2.index:
            if file_ not in f1.index: # file unknown to f1
                self.transfer(f2, f1, file_)

    def transfer(self, source_from, source_to, path):
        versions1 = source_from.index[path]
        versions2 = source_to.index.get(path, [])
        if versions1[-1][0] == False: # file to delete
            if len(versions2) != 0 and versions2[-1][0] == True:
                if not self.confirm_delete(source_from, source_to, path):
                    return
                if self.no_trash:
                    source_to.delete(path)
                else:
                    source_to.rename(path, os.path.join(BISYNC_TRASH, path))
        else: # file to copy
            if len(versions2) == 0 or versions2[-1] == [False]:
                if not self.confirm_copy(source_from, source_to, path):
                    return
            else:
                if not self.confirm_replace(source_from, source_to, path):
                    return
            tmp = path + BISYNC_SUFFIX
            source_to.copy_to(source_from.get_local_name(path), tmp)
            source_to.rename(tmp, path)

        self.merge_versions(source_from, source_to, path)

    def confirm_copy(self, source_from, source_to, path):
        return True

    def confirm_delete(self, source_from, source_to, path):
        return True

    def confirm_replace(self, source_from, source_to, path):
        return True

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
        # automatic conflict resolution, takes the last modified file
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
        
class CmdSynchronizer(Synchronizer):
    def __init__(self, cmd_args, **kwargs):
        super(CmdSynchronizer, self).__init__(**kwargs)
        self.args = cmd_args

    def get_file_desc(self, source, path):
        last = source.index.get(path, [[False]])[-1]
        if last[0] == True:
            return "%s %s (%.1f kb, last modif: %s)" % (source.get_name(), path,
                last[1] / 1000., str(datetime.datetime.fromtimestamp(last[2])))
        else:
            return "%s %s" % (source.get_name(), path)

    def confirm_copy(self, source_from, source_to, path):
        if self.args.auto:
            return True
        print "File copy"
        print "From: %s" % self.get_file_desc(source_from, path)
        print "To: %s" % self.get_file_desc(source_to, path)
        result = (raw_input("Confirm ? ([Y]es, [n]o) ").strip() or " ")[0].lower()
        if result == "n":
            return False
        else:
            return True

    def confirm_delete(self, source_from, source_to, path):
        if self.args.auto:
            return True
        print "File delete"
        print "In: %s" % self.get_file_desc(source_to, path)
        result = (raw_input("Confirm ? ([Y]es, [n]o) ").strip() or " ")[0].lower()
        if result == "n":
            return False
        else:
            return True

    def confirm_replace(self, source_from, source_to, path):
        if self.args.auto:
            return True
        print "File overwrite"
        print "From: %s" % self.get_file_desc(source_from, path)
        print "To: %s" % self.get_file_desc(source_to, path)
        result = (raw_input("Confirm ? ([Y]es, [n]o) ").strip() or " ")[0].lower()
        if result == "n":
            return False
        else:
            return True

    def resolve_conflict(self, f1, f2, path):
        ans = super(CmdSynchronizer, self).resolve_conflict(f1, f2, path)
        if self.args.full_auto:
            return ans
        print "Conflict!"
        print "Left: %s" % self.get_file_desc(f1, path)
        print "Right: %s" % self.get_file_desc(f2, path)
        if ans == 1:
            result = (raw_input("Which one ? ([L]eft, [r]ight) ").strip() or " ")[0].lower()
            if result == "r":
                ans = 2
        else:
            result = (raw_input("Which one ? ([l]eft, [R]ight) ").strip() or " ")[0].lower()
            if result == "l":
                ans = 1
        return ans

def main():
    parser = argparse.ArgumentParser(description='Synchronize two folders.')
    parser.add_argument('folders', metavar='folders', type=str, nargs='+',
                       help='Folders to synchronize')
    parser.add_argument("-s", "--simulation", help="Only output operations", action="store_true")
    parser.add_argument("-a", "--auto", help="Does not confirm file transfers", action="store_true")
    parser.add_argument("-f", "--full-auto", help="Does not confirm file transfers" +
        " and resolve conflicts automatically", action="store_true")
    parser.add_argument("-t", "--no-trash", help="Deletes files instead of sending them to a trash" +
        " folder", action="store_true")

    args = parser.parse_args()
    if args.full_auto:
        args.auto = True
    if args.simulation:
        args.no_trash = True

    sync = CmdSynchronizer(args, no_trash=args.no_trash)

    if not args.simulation:
        sources = [FileSystemSource(x) for x in args.folders]
    else:
        sources = [FileSystemSimulationSource(x) for x in args.folders]
    sync.synchronize_all(sources)

