Bisync
======

A distributed bidirectional folder synchronizer.

I created this program mainly to handle a large music collection, but it could also be useful for lot of other uses.
Basically, it keeps an history of file versions in each separate folders, which allows it to detect file deletion,
file rename, understand when a file was updated in a folder but not in an other, detect conflicting modifications, etc...
It's also fully distributed, so you can sync your desktop with your laptop, then your laptop with your tablet, then your
tablet back with your desktop, etc...

Currently it only supports local folders sync, I plan to implement ssh as soon as I have time to do so. Although
it will work with sshfs.

To test it:

    sudo pip install bisync
    bisync folder1 folder2

For the upcoming questions:

####Why is it better than rsync?
Because bisync is bidirectional and rsync can't track deletions, renames nor changes on the two sides.

####Why is it better than unison?
Because unison is centralized, which mean you have to always use the same computer to make the synchronisation. I can't
help but think it's super boring, because today a lot of people have more than 2 computers (desktop + laptop + tablet +
smartphone + working pc + grandma's pc, etc...).

####Why is it better than git/mercurial?
Because those are *real* DVCS, they keep a copy of each file versions, they create diffs, they compute hashs of files...
All of that will take far too much time for a 200G mp3 collection and will take at least twice the disk size
normaly occupied by the files. Bisync does not do that, it only checks files metadata and store them in its history.
That makes it *a lot* faster and makes the additional disk usage insignificant. Of course, you can't go back in
history, which is a problem for code, not for mp3.

####Why is it better than Dropbox?
Go check how much it cost to host 200G on Dropbox and you'll know. Also, bisync is GPL.

###Changelog:
- 0.8.0:
  - First released version
