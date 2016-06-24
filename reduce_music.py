#!/usr/bin/python
# reduce_music.py
# assuming you are in your home directory on OS X,
# converts all music in Music/iTunes to smaller AAC files
# into Music/Smaller, preserving directory structure
# and of course the original files.
# Three CPU cores are used (why only three?)
# Files with a bitrate <= 130 kbps are not converted but copied.
#
# Options:
# -n : simulate only, do not convert any files.

from __future__ import print_function
import multiprocessing
import os
import re
import shutil
import subprocess
import sys

# just to get more distinct feedback when something goes wrong
class NotAMusicFileException(Exception):
    pass

def run_or_simulate(cmd, *args):
    if '-n' in sys.argv:
        print ('simulating call to %s with arguments %s' % (cmd, args))
    else:
        cmd(*args)

def needs_converting(in_file):
    print('calling afinfo on %s' % in_file)
    aifinfo_output = subprocess.check_output(['afinfo', in_file])
    pattern = 'bit rate: ([0-9]+) bits per second'
    return int(re.search(pattern, aifinfo_output).group(1)) > 130000 

def map_to_pool(func, data):
    pool = multiprocessing.Pool(3) # why not use all cores?
    results = pool.map(func, data)
    pool.close()
    pool.join()
    return results

# uses Apple's afconvert command line utility to convert an audio
# file to an intermediate file, and then to an AAC result file.
def convert_files(in_file, out_file, intermediate_file):
    try:
        print('calling afconvert on %s' % in_file)
        [run_or_simulate(x, y) for x, y in (
            (subprocess.check_call, ['afconvert', in_file,
            intermediate_file, '-d', '0', '-f', 'caff',
            '--soundcheck-generate']),

            (subprocess.check_call, ['afconvert', intermediate_file,
            '-d', 'aach', '-f', 'm4af', '--soundcheck-read',
            '-b', '80000', '-q', '127', '-s', '2', out_file]),

            (os.remove, intermediate_file))]
    except subprocess.CalledProcessError as e:
        print('afconvert first run failed.')
        try:
            run_or_simulate(subprocess.check_call, ['afconvert', in_file,
                out_file, '-d', 'aach', '-f', 'm4af',
                '-b', '80000', '-q', '127', '-s', '2'])
        except Exception as e:
            return e
    return None

def convert_files_triple(args):
    return convert_files(*args)
    
def analyze_directory_structure(source_dir):
    music_files = []
    subdirs_to_create = []
    for my_dir, subdirs, files in os.walk(source_dir):
    
        if my_dir.find('Podcasts') >= 0:
            continue
        in_files = [os.path.join(my_dir, f) for f in files
                if f.lower().endswith(music_extensions)]
        if in_files:
            music_files += in_files
            subdirs_to_create.append(my_dir)
    return music_files, subdirs_to_create
    

# main function is definitely too long and hard to read with interleaved
# function defs and other statements. I should split that up
if __name__ == '__main__':

    # global constants - TODO: give user an option to select dirs
    music_dir = 'Music/iTunes'
    music_extensions = ('.mp3', '.m4a', '.wav', '.aif')
    target_dir = 'Music/Smaller'
    
    music_files, subdirs_to_create = analyze_directory_structure(music_dir)
  
    def getm4afile(f):
        (root, ext) = os.path.splitext(f)
        return root + '.m4a'

    def join_to_target(f):
        return os.path.join(target_dir, f)

    new_music_files = [f[0] for f in
        zip(music_files, [join_to_target(f) for f in music_files],
        [join_to_target(getm4afile(f)) for f in music_files])
        if not any((os.path.exists(x) for x in f[1:]))]

    results = map_to_pool(needs_converting, new_music_files)
    
    files_to_convert = [f[1] for f in zip(results, new_music_files) if f[0]]
    files_to_copy = [f for f in new_music_files if not f in files_to_convert]
    
    def get_outfile_for(in_file):
        if not in_file.lower().endswith(music_extensions):
            raise NotAMusicFileException()
        if in_file in files_to_convert:
            return getm4afile(in_file)
        else:
            return in_file
    
    def get_target_outfiles_for(l):
        return [join_to_target(get_outfile_for(f)) for f in l]

    def strip_existing_targets(in_list):
        return [x for x in in_list if not os.path.isfile(list(x)[1])]
   
    copy_infiles_outfiles = strip_existing_targets(
            zip(files_to_copy, get_target_outfiles_for(files_to_copy)))

    # intermediate files are stored here.
    temp_dir = os.path.join(target_dir, 'tmp')

    dirs_to_create = [x for x in map(join_to_target, subdirs_to_create)
            + [temp_dir] if not os.path.isdir(x)]
    
    intermediate_files = [os.path.join(temp_dir,
        'intermediate%d.caf' % id_number)
        for id_number in range(len(files_to_convert))]

    convert_in_out_intermediate_files = strip_existing_targets(
            zip(files_to_convert,
                get_target_outfiles_for(files_to_convert), intermediate_files))
    
    [run_or_simulate(os.makedirs, d) for d in dirs_to_create]
    [run_or_simulate(shutil.copy, *p) for p in copy_infiles_outfiles]
    
    results = map_to_pool(convert_files_triple, convert_in_out_intermediate_files)
    
    print('%d files copied - %d files converted.'
            %(len(copy_infiles_outfiles), len(convert_in_out_intermediate_files)))
    if any(results):
        print('Errors eccured:')
        [print(e) for e in results if e]

