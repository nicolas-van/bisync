Bisync
======

A distributed bidirectional folder synchronizer.

I created this program mainly to handle a large music collection, but it could also be useful for lot of other uses.
Basically, it keeps an history of file versions in each separate folders, which allow it to detect file deletion,
file rename, understand when a file was updated in a folder but not in an other, detect conflicting modifications, etc...

Of course it's not a safe as git or mercurial because it can't got back in history. But for large collections of files,
like the typical case of a mp3 collection, it's hundred times faster and won't use twice the disk size.

To test it:

    sudo pip install bisync
    bisync folder1 folder2


###Changelog:
- 0.8.0:
  - First released version
