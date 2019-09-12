# SweepText
Sweeptext scans through text notes like those used by SimpleNote,
NotationalVelocity, or any text editor and finds lines matching patterns and
moves (refiles) or copies (collects) those lines to target files.

I use this to keep my plain text organization files in order.
In my _inbox.txt I simply add [tag] to the beginning of a line to have it
auto-refile (move) to the file with that name, ie: tag.txt
I also add #todo or #errand anywhere on a line to have it collected (copied)
to #todos.txt or #errands.txt respectively. It handles some details more
gracefully than a collection of grep, sed and awk scripts would.

Here is my batch/shell script:
```
cd D:\Dropbox\Simplenote
sweeptext -refile '^\[{note}\] ' -from "_inbox.txt" -to "{note}.txt"
sweeptext -collect '#todo' -from "*" -exclude "* (collected).txt" -to "#todos (collected).txt"
sweeptext -collect '#errand' -headers -from "*" -exclude " (collected).txt" -to "#errands (collected).txt"
```

-refile or -move will find lines matching pattern, remove them from the source
    file, insert them into the target file. The pattern can be a glob "\*" or a
    regex "/^\w+/". All lines moved from a source file are inserted into the
    target file in the same order they were found. Each line in a source file
    can be moved to a different target file by using a named {word} in the
    target file name, eg: -refile "#{tag}" -to "hash-{tag}.txt".
    Sets the following options: "-cleanmatch -noaddlinks -noaddheaders -insert afterblank".
    A string matched in the pattern can be used as part of the filename in the
    target -to <file>, eg: -refile "#{tag}" -to "hash-{tag}.txt".
    Note: The special syntax {word} has been added to name patterns in regex,
    it is equivelant to "{word}" -> "(?P<word>.*?)\\b".
    If the target "to" file doesnt exist, do not create it,
    skip it to protect against typos.
 
-collect or -copy will find lines matching pattern, copy them to the target file.
    The target file is wiped and recreated with each run.
    Sets the following options: "-nocleanmatch -noaddlinks -addheaders -insert overwrite".
    If the target 'to' file doesnt already exist, do not create it to protect against typos.
    
```
usage: sweeptext.py [-h]
                    (-refile [pattern] | -move [pattern] | -collect [pattern] | -copy [pattern])
                    [-addlinks | -noaddlinks] [-cleanmatch | -nocleanmatch]
                    [-addheaders | -noaddheaders] [-insert [location]] [-test]
                    [-debug] [-v] [-rulesfile [filename]]
                    [-folder [foldername]] [-from [filenameglob-or-regex]]
                    [-exclude [filenameglob-or-regex]] -to [filename]

Sweeptext scans through text notes like those used by SimpleNote,
NotationalVelocity, or any text editor and finds lines matching patterns and
moves (refiles) or copies (collects) those lines to target files.

-refile or -move will find lines matching pattern, remove them from the source
    file, insert them into the target file. The pattern can be a glob "*" or a
    regex "/^\w+/". All lines moved from a source file are inserted into the
    target file in the same order they were found. Each line in a source file
    can be moved to a different target file by using a named {word} in the
    target file name, eg: -refile "#{tag}" -to "hash-{tag}.txt"
    Sets the following options: -cleanmatch -noaddlinks -noaddheaders -insert afterblank
    A string matched in the pattern can be used as part of the filename in the
    target -to <file>, eg: -refile "#{tag}" -to "hash-{tag}.txt"
    Note: The special syntax {word} has been added to name patterns in regex,
    it is equivelant to "{word}" -> "(?P<word>.*?)\b"
    If the target "to" file doesnt exist, do not create it,
    skip it to protect against typos.

-collect or -copy will find lines matching pattern, copy them to the target file
    The target file is wiped and recreated with each run.
    Sets the following options: -nocleanmatch -noaddlinks -addheaders -insert append
    If the target 'to' file doesnt already exist, do not create it to protect against typos

optional arguments:
  -h, --help            show this help message and exit
  -refile [pattern]     Find lines matching pattern, remove them from the
                        source file, insert them into the target file
  -move [pattern]       alias for -refile
  -collect [pattern]    Find lines matching pattern, copy them to the target
                        file. The target file is wiped and restarted with each
                        run.
  -copy [pattern]       alias for -collect
  -addlinks             Add a link back to the source file at the end of the
                        line in the form: [[sourcefile]]
  -noaddlinks           Don't add a link back to the source file at the end of
                        the line
  -cleanmatch           Remove the matched pattern from the line
  -nocleanmatch         Don't remove the matched pattern from the line
  -addheaders           adds a header line before each group in the form:
                        [[sourcefile]]
  -noaddheaders         Don't add a header line before each group
  -insert [location]    Specified where inserted lines should be placed:
                        'afterblank', 'top', 'append', 'overwrite'. Note 'top'
                        would be disasterous for Simplenote files because the
                        first line is the title
  -test                 run and report on what it would do but don't actually
                        change anything
  -debug                print great detail of information, much more than
                        verbose
  -v, --verbose         print what is being done
  -rulesfile [filename]
                        Specifies a text file containing arguments for
                        multiple batched runs of sweeptext, one run per line
  -folder [foldername]  name of the folder to scan (Default "."
  -from [filenameglob-or-regex]
                        Specifies the source files to scan. Can contain a glob
                        "*.txt" or regex "/[0-9].*\.txt/" (Default "*.txt")
  -exclude [filenameglob-or-regex]
                        Specifies source files to skip. Can contain a glob
                        "*.txt" or regex "/[0-9].*\.txt/" (Default none)
  -to [filename]        Specified the target file(s) to insert matched lines
                        into. Can include a matched word from the match
                        pattern, eg: "collected {tag}.txt"
```
