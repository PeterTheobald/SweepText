#!python

# sweeptext.py
# peter@PeterTheobald.com 2019
#
# aka SimpleSweep aka RefileCollect aka CloudGrep
# aka 'Crepe' (cloud regular expression pattern evaluator)
#
# Scans through text notes like those used by SimpleNote, NotationalVelocity,
# DropBox + an editor etc and finds lines matching patterns and
# moves (refiles) or copies (collects) them to other files
#
# I use this to keep my plain text organization files in order.
# In my _inbox.txt I simply add [tag] to the beginning of a line to have it
# auto-refile (move) to the file with that name, ie: tag.txt
# I also add #todo or #errand anywhere on a line to have it collected (copied)
# to #todos.txt or #errands.txt respectively. It handles some details more
# gracefully than a collection of grep, sed and awk scripts would.
#
# Here is my batch/shell script:
# cd D:\Dropbox\Simplenote
# sweeptext -refile '^\[{note}\] ' -from "_inbox.txt" -to "{note}.txt"
# sweeptext -collect '#todo' -from "*" -exclude "* (collected).txt" -to "#todos (collected).txt"
# sweeptext -collect '#errand' -headers -from "*" -exclude " (collected).txt" -to "#errands (collected).txt"

# alternatively I can put these three lines in a text file and call:
# sweeptext -rulesfile my_three_lines.cfg -folder "D:\Dropbox\Simplenote"

# A future version of this could run as a cloud service directly on the
# SimpleNote, Dropbox, EverNote, OneNote, GoogleDocs etc APIs

# Note: First implementations won't support all these options, just the minimum necessary to run my sample script above
#       Specifically: -refile -collect -from -to -test

# Note: Be careful throughout, we are reading from files and overwriting/inserting into the same files
#       lots of potential for problems there. Use read, write to temp file, rename. os.rename() is atomic
#       Also other systems eg Dropbox Simplenote etc can be reading and writing to these at the same time
#       race conditions abound for when we read and update the files.
#       We could scan a file, write the new temp file, then dropbox updates the file (atomically),
#       then we rename and lose Dropbox's changes

# TODO: add -create -nocreate; create a new target file if it doesnt already exist, currently default to NOT create new files
# TODO: add -addlink "format-pattern" eg: -addlink "[[{name}]]" or -addlink "<a href='{name}.html'>{name}</a>"
# TODO: add -insert "afterpattern" <pattern>, add -insert "line:<n>", eg: -insert "afterpattern:-----"
# TODO: someday/maybe "crepe" (cloud regular expression engine)
#       run as a service in the cloud against Dropbox, Simplenote, GDocs, OneNote, EverNote APIs (etc)
#       (put the rulesfile in a named note/document)
#       make available publically for free once/day up to some limit of num notes. small $ for realtime updates.
# TODO: someday/maybe add rules for full ability of 'grep', 'sed', 'awk' tools in the document.
#       add ability to enter rule to the end of any document and have it 
#       send output to another file or appended to the current file
# TODO: someday/maybe add a full repl ("creplach"? :-) ) any cloud document by
#       entering command at the bottom and having the output appear below
# Optimization TODOs:
# 1. A large improvement in speed can be found for multiple sequential runs of sweeptext
# Instead of scanning all source files over again with each pass of sweeptext, 
# load a list of runs from a '-rulesfile' and scan for all patterns during one pass
# or, more accurately, two passes. One pass for -refile(s) and a second pass for -collect(s)
# because -refile alters the source files so -collect should be run on the updated source files
# 2. Rewrite this in Rust or call Rust's incredibly fast RipGrep libraries


import sys
import os
import shutil
import argparse
import shlex
import re
import fnmatch

descriptive_text = """
Sweeptext scans through text notes like those used by SimpleNote,
NotationalVelocity, or any text editor and finds lines matching patterns and
moves (refiles) or copies (collects) those lines to target files.
 
-refile or -move will find lines matching regex pattern, remove them from the source
    file, insert them into the target file. All lines moved from a source file are
    inserted into the target file in the same order they were found. Each line in a
    source file can be moved to a different target file by using a named {word} in the
    target file name, eg: -refile "#{tag}" -to "hash-{tag}.txt"
    Sets the following options: -cleanmatch -noaddlinks -noaddheaders -insert afterblank
    A string matched in the pattern can be used as part of the filename in the
    target -to <file>, eg: -refile "#{tag}" -to "hash-{tag}.txt"
    Note: The special syntax {word} has been added to name patterns in regex,
    it is equivelant to "{word}" -> "(?P<word>.*?)\\b"
    If the target "to" file doesnt exist, do not create it,
    skip it to protect against typos.
 
-collect or -copy will find lines matching pattern, copy them to the target file
    The target file is wiped and recreated with each run.
    Sets the following options: -nocleanmatch -noaddlinks -addheaders -insert append
    If the target 'to' file doesnt already exist, do not create it to protect against typos
"""

def main():
    parser=argparse.ArgumentParser( description=descriptive_text, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument( '-refile', nargs='?', metavar='pattern', help='Find lines matching pattern, remove them from the source file, insert them into the target file')
    group.add_argument( '-move', nargs='?', metavar='pattern', help='alias for -refile')
    group.add_argument( '-collect', nargs='?', metavar='pattern', help='Find lines matching pattern, copy them to the target file. The target file is wiped and restarted with each run.')
    group.add_argument( '-copy', nargs='?', metavar='pattern', help='alias for -collect')
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument( '-addlinks', action='store_true', help='Add a link back to the source file at the end of the line in the form: [[sourcefile]]')
    group2.add_argument( '-noaddlinks', action='store_true', help='Don\'t add a link back to the source file at the end of the line')
    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument( '-cleanmatch', action='store_true', help='Remove the matched pattern from the line')
    group3.add_argument( '-nocleanmatch', action='store_true', help='Don\'t remove the matched pattern from the line')
    group4 = parser.add_mutually_exclusive_group()
    group4.add_argument( '-addheaders', action='store_true', help='adds a header line before each group in the form: [[sourcefile]]')
    group4.add_argument( '-noaddheaders', action='store_true', help='Don\'t add a header line before each group')
    parser.add_argument( '-insert', nargs='?', metavar='location', help="Specified where inserted lines should be placed: 'afterblank', 'top', 'append', 'overwrite'. Note top would be disasterous for Simplenote files because the first line is the title")
    parser.add_argument( '-test', action='store_true', help='run and report on what it would do but don\'t actually change anything')
    parser.add_argument( '-debug', action='store_true', help='print great detail of information, much more than verbose')
    parser.add_argument( '-v', '--verbose', action='store_true', help='print what is being done')
    parser.add_argument( '-rulesfile', nargs='?', metavar='filename', help='Specifies a text file containing arguments for multiple batched runs of sweeptext, one run per line')
    parser.add_argument( '-folder', nargs='?', metavar='foldername', default='.', help='name of the folder to scan (Default "."')
    parser.add_argument( '-from', nargs='?', metavar='filenameglob-or-regex', dest='fromfiles', default='*.txt', help='Specifies the source files to scan. Can contain a glob "*.txt" or regex "[0-9].*\.txt" (Default "*.txt")')
    parser.add_argument( '-exclude', nargs='?', metavar='filenameglob-or-regex', help='Specifies source files to skip. Can contain a glob "*.txt" or regex "[0-9].*\.txt" (Default none)')
    parser.add_argument( '-to', nargs='?', metavar='filename', required=True, help='Specified the target file(s) to insert matched lines into. Can include a matched word from the match pattern, eg: "collected {tag}.txt"')
    args=parser.parse_args()
    process_args( args)
    if (args.verbose): print( args)
    run( args)

def process_args( args):

    if args.rulesfile:
        print( ' -rulesfiles has not been implemented yet. Please put batch runs in a script or batch file.', file=sys.stderr)
        sys.exit(1)
    if args.refile:
        args.action='move'
        args.pattern=args.refile
    if args.move:
        args.action='move'
        args.pattern=args.move
    if args.collect:
        args.action='copy'
        args.pattern=args.collect
    if args.copy:
        args.action='copy'
        args.pattern=args.copy

    # set appropriate defaults
    if args.action=='move':
        args.do_addlinks=False
        args.do_cleanmatch=True
        args.do_addheaders=False
        args.do_insert='afterblank'
    if args.action=='copy':
        args.do_addlinks=False
        args.do_cleanmatch=False
        args.do_addheaders=True
        args.do_insert='overwrite'
    # Override defaults with requested values
    if args.addlinks: args.do_addlinks=True
    if args.noaddlinks: args.do_addlinks=False
    if args.cleanmatch: args.do_cleanmatch=True
    if args.nocleanmatch: args.do_cleanmatch=False
    if args.addheaders: args.do_addheaders=True
    if args.noaddheaders: args.do_addheaders=False
    if args.insert: args.do_insert=args.insert
    if args.test: args.verbose=True
    if args.debug: args.verbose=True

# algorithm:
# 1. find all matching lines in source files:
# for all matching source files:
#   for all lines:
#       save matching lines to memory by target: lines[target].append(line)
#       (-refile only) write all non-matching lines to source.sweeptmp file
# 2. insert all matched lines in their targets
# for all target files referenced in memory:
#      if file has been updated by -refile removals, make the swap
#          mv target -> target.1.old; mv target.sweeptmp -> target
#      copy all lines up to INSERT point to target.sweeptmp (fast copy for append)
#      write all matched lines in memory to target.sweeptmp
#      copy remainder of lines from INSERT point down to target.sweeptmp
#      mv target -> .target.1.old; mv target.sweeptmp -> target
# for all source files updated by -refile removals (not yet swapped)
#     mv source -> .source.1.old; mv source.sweeptmp -> source
# (note get file locks on these while they are being updated)

    
def run( args):
    
    if args.fromfiles[0]=='/' and args.fromfiles[-1]=='/':
        source_file_regex = args.fromfiles[1:-1] # cut off slashes, keep regex
    else:
        source_file_regex = fnmatch.translate( args.fromfiles) # convert glob to regex
    if args.exclude:
        if args.exclude[0]=='/' and args.exclude[-1]=='/':
            exclude_file_regex = args.exclude[1:-1] # cut off slashes, keep regex
            if (args.debug): print('EXCLUDING REGEX ',exclude_file_regex)
        else:
            exclude_file_regex= fnmatch.translate( args.exclude) # convert glob to regex
            if (args.debug): print('EXCLUDING GLOB ',args.exclude,' = REGEX ',exclude_file_regex)

    # handle special pattern syntax {name}, change into regex (?P<name>.*?)\b
    pattern_regex = re.sub( "{([a-zA-Z]\w*)}", lambda match: '(?P<'+match.group(0)[1:-1]+'>.*?)\\b', args.pattern)
    if (args.debug): print('pattern_regex=',pattern_regex)
    # must start w a-zA-Z so we don't clobber regex counting operator {n}
    
    insert_lines={} # insert_lines[targetnote].append(line)
    # TODO: if memory gets low, append insert_lines to temp files instead of memory
    updated_sources=[] # keep track of source files with removed lines
    doesnt_exist=[] # don't move lines if the target file doesnt exist, track those to avoid lots of stat calls

    # find all matching lines in source files:
    prev_file=None
    for direntry in sorted(os.scandir( args.folder), key=lambda d: d.name.lower()):
        if not re.match( source_file_regex, direntry.name):
            continue # skip files that don't match the FROM pattern
        if args.exclude and re.match( exclude_file_regex, direntry.name):
            if (args.verbose): print("SKIP ",direntry.name)
            continue # skip files that match the EXCLUDE pattern
        if direntry.name.endswith('.old'):
            continue # skip sweeptext backup files
        if args.verbose: print('Reading ',direntry.name)
        
        with open( os.path.join( args.folder, direntry.name), encoding='utf-8') as file:
            updated_tmpfile=False
            for line in file:
                pattern_match=re.search( pattern_regex, line)
                # if the pattern matches and the target file exists, move or copy it to the target
                # if we are in move mode and (the pattern doesnt match or the target file doesnt exist), copy the line (preserve) to the temp file
                if pattern_match:
                    # found a matching line
                    # calc the target file for it args.to with any {name} substituted
                    # get the {name} in args.to, lookup the corresponding named group on the line in pattern_match
                    target=re.sub( "{([a-zA-Z]\w*)}", lambda sub_match: pattern_match.group(sub_match.group(0)[1:-1]), args.to)
                    if target in doesnt_exist or not os.path.exists( os.path.join( args.folder, target)):
                        # if the target doesn't already exist, don't move or copy this line
                        if args.verbose: print('  ',target,' does not exist, skipping line')
                        doesnt_exist.append( target)
                    else: # target file exists
                        if args.do_cleanmatch:
                            line=line.replace( pattern_match.group(0), '') # remove matched text - plain text not a regex
                        if args.do_addlinks:
                            line=line+' ['+os.path.splitext(direntry.name)[0]+']'
                        if args.do_addheaders and prev_file!=direntry.name:
                            additem( insert_lines, target, '\n['+os.path.splitext(direntry.name)[0]+']\n')
                            prev_file=direntry.name
                            if (args.debug): print( '  TO: ',target, ' Header : ['+os.path.splitext(direntry.name)[0]+']')
                        additem( insert_lines, target, line)
                        if args.debug: print( '  TO: ',target,line, end='')
                if args.action=='move' and (not pattern_match or target in doesnt_exist or not os.path.exists( os.path.join( args.folder, target))):
                    # if we are in move mode and (the pattern doesnt match or the target file doesnt exist), copy the line (preserve) to the temp file
                    # remove matched lines by copying unmatched lines to tmp file
                    if not updated_tmpfile:
                        source_tmpfile = open( os.path.join( args.folder, direntry.name+'.swtxttmp'), encoding='utf-8', mode='w')
                        updated_tmpfile=True
                        updated_sources.append( direntry.name)
                    print( line, file=source_tmpfile, end='')
        if updated_tmpfile:
            source_tmpfile.close()
    # insert all matched lines in their targets
    for target in insert_lines:
        if args.verbose: print('Writing to ',target)
        if target in updated_sources:
            # if the target has been updated by -refile, first apply any updates
            if not args.test: apply_file_update( target, args.folder)
            updated_sources.remove( target)
        if args.do_insert=='top':
            # insert the matched lines to the TOP of target
            # first copy matched lines, then original contents of target
            with open( os.path.join( args.folder, target)+'.swtxttmp', encoding='utf-8', mode='w') as tempfile:
                tempfile.writelines( insert_lines[target])
                with open( os.path.join( args.folder, target), encoding='utf-8') as targetfile:
                    shutil.copyfileobj( targetfile, tempfile)
        if args.do_insert=='append':
            # insert the matched lines to the BOTTOM of target
            # first copy the original contents of target, then append the matched lines
            shutil.copy( os.path.join( args.folder, target), os.path.join( args.folder, target)+'.swtxttmp')
            with open( os.path.join( args.folder, target)+'.swtxttmp', encoding='utf-8', mode='a') as tempfile:
                tempfile.writelines( insert_lines[target])
        if args.do_insert=='overwrite':
            # overwrite the file with the matched lines
            with open( os.path.join( args.folder, target)+'.swtxttmp', encoding='utf-8', mode='w') as tempfile:
                tempfile.writelines( insert_lines[target])
        if args.do_insert=='afterblank':
            # insert the matched lines IN THE MIDDLE of target, after the first blank line
            # first copy the top of the original file, then the matched lines, then the rest of the original file
            inserted_lines=False
            with open( os.path.join( args.folder, target)+'.swtxttmp', encoding='utf-8', mode='w') as tempfile:
                with open( os.path.join( args.folder, target), encoding='utf-8') as targetfile:
                    for line in targetfile:
                        if line=='\n' and not inserted_lines:
                            print( line, file=tempfile, end='') # blank before and after inserted lines
                            tempfile.writelines( insert_lines[target])
                            inserted_lines=True
                        print( line, file=tempfile, end='')
                    if not inserted_lines: # empty file, or no blank lines: append
                        tempfile.writelines( insert_lines[target])
        if args.verbose: sys.stdout.writelines( ['  '+s for s in insert_lines[target]])
        # replace the target file with the new updated version
        if not args.test: apply_file_update( target, args.folder)

    # finally, for all sources that were updated with removed -refile lines, apply the updates
    if not args.test:
        for target in updated_sources:
            apply_file_update( target, args.folder)

def additem( list, index, item):
    if index in list:
        list[index].append(item)
    else:
        list[index]=[ item ]
        
def apply_file_update( file, folder):
    # applies changes in a temp file to the original file, with backups
    path=os.path.join( folder, file)
    if (os.path.exists( path+'.swtxt~2')): os.replace( path+'.swtxt~2', path+'.swtxt~3')
    if (os.path.exists( path+'.swtxt~1')): os.rename( path+'.swtxt~1', path+'.swtxt~2')
    os.rename( path, path+'.swtxt~1')
    os.rename( path+'.swtxttmp', path)

if __name__=='__main__':
    main()

