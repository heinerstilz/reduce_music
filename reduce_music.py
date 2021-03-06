#!/usr/bin/python2
# reduce_music.py
#
# Heiner Stilz 2015
# heinerstilz@gmail.com
#
# assuming you are in your home directory on OS X,
# converts all music in Music/iTunes to smaller AAC files
# into Music/Smaller, preserving directory structure
# and of course the original files.
# All CPU cores are used.
# Files with a bit rate <= 130 kbps are not converted but copied
# to save time and avoid the worst reconversion losses.
# target bit rate is arount 80 kbps (yes, my old phone's memory
# card WAS small).
#
# Tested with Python 2.7.10
#
# Options:
# -m <MusicDir> : convert music from <MusicDir>/ instead of Music/iTunes
# -n : simulate only, do not convert any files.
#
# TODO:
# - more tests
# - option to choose target bit rate
# - option to choose conversion threshold
# - option to choose temp and target dirs
# - target folder structure is too deeply nested
# - option to deactivate multiprocessing

from __future__ import print_function
import functools
import multiprocessing
import os
import re
import shutil
import subprocess
import sys

# just to get more distinct feedback when something goes wrong
class NotAMusicFileException(Exception):
    pass


# makes it convenient for client code to run certain functions
# conditionally
# TODO: undecorate, just wrap the function calls and KISS
def run_or_simulate(func):

    @functools.wraps(func)
    def decorate(*args):
        if '-n' in sys.argv:
            print ('simulating call to %s with arguments %s' % (func, args))
        else:
            func(*args)

    return decorate


@run_or_simulate
def check_call(*args):
    return subprocess.check_call(*args)

@run_or_simulate
def remove(*args):
    return os.remove(*args)

@run_or_simulate
def makedirs(*args):
    return os.makedirs(*args)

@run_or_simulate
def copy(*args):
    return shutil.copy(*args)


# executes on func on the given argument lists in a multiprocessing pool.
def map_to_pool(func, data):
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    results = pool.map(func, data)
    pool.close()
    pool.join()
    return results

# uses Apple's afinfo utility and parses its output to
# decide whether an audio file's output has a bitrate
# large enough to justify converting.
# More on afinfo:
# http://osxdaily.com/2010/10/19/get-mp3-file-info-on-mac
# or, on a Mac, afinfo -h
# I just noticed there is a xml output option...
# Wouldn't it be more stable to use that??
def needs_converting(in_file):
    print('calling afinfo on %s' % in_file)
    aifinfo_output = subprocess.check_output(['afinfo', in_file])
    pattern = 'bit rate: ([0-9]+) bits per second'
    return int(re.search(pattern, aifinfo_output).group(1)) > 130000 

# uses Apple's afconvert command line utility to convert an audio
# file to an intermediate file, and then to an AAC result file.
# See
#http://images.apple.com/itunes/mastered-for-itunes/docs/mastered_for_itunes.pdf
# on afconvert options and how to use it with an intermediate file.
# Or, on a Mac, type afconvert -h
def convert_files(in_file, out_file, intermediate_file):
    try:
        print('calling afconvert on %s' % in_file)
        check_call(['afconvert', in_file,
            intermediate_file, '-d', '0', '-f', 'caff',
            '--soundcheck-generate'])

        check_call(['afconvert', intermediate_file,
            '-d', 'aach', '-f', 'm4af', '--soundcheck-read',
            '-b', '80000', '-q', '127', '-s', '2', out_file])

        remove(intermediate_file)
    except subprocess.CalledProcessError as e:
        print('afconvert first run failed.')
        # in this case, most of the time it works
        # without an intermediate file. No idea why.
        try:
            check_call(['afconvert', in_file,
                out_file, '-d', 'aach', '-f', 'm4af',
                '-b', '80000', '-q', '127', '-s', '2'])
        # why catch all exceptions here and only one above?
        # No exception should leace this function, as it's
        # supposed to run within a multiprocessing pool
        except Exception as e:
            return e
    return None

def convert_files_l(args):
    return convert_files(*args)
    

class PathCalcualtor:

    def __init__(self):
        # global constants 
        try:
            # will throw if option is not specified
            self.music_dir = sys.argv[sys.argv.index('-m') + 1]
            if not os.path.exists(self.music_dir):
                print('path %s does not exist.' % self.music_dir)
                print('Using default directory')
                raise Exception()
        except Exception:
            self.music_dir = os.path.join('Music', 'iTunes')
        self.music_extensions = ('.mp3', '.m4a', '.wav', '.aif')

        # TODO: give user an option to select dirs
        self.target_dir = os.path.join('Music', 'Smaller')
        self.temp_dir = os.path.join(self.target_dir, 'tmp')

    
    @staticmethod
    def to_m4a_filename(path):
        (root, ext) = os.path.splitext(path)
        return root + '.m4a'

    def to_target_dir(self, f):
        return os.path.join(self.target_dir, f)

    # finds music files and subdirectories containing those
    # in self.music_dir.
    def analyze_directory_structure(self):
        music_files = []
        subdirs_to_create = []
        for my_dir, subdirs, files in os.walk(self.music_dir):
        
            if my_dir.find('Podcasts') >= 0:
                continue
            in_files = [os.path.join(my_dir, f) for f in files
                    if f.lower().endswith(self.music_extensions)]
            if in_files:
                music_files += in_files
                subdirs_to_create.append(my_dir)
        return music_files, subdirs_to_create

    # Changes the extension to 'm4a' if in_file is in files_to_convert.
    # Identity otherwise.
    def get_outfile_for(self, in_file, files_to_convert):
        if not in_file.lower().endswith(self.music_extensions):
            raise NotAMusicFileException()
        if in_file in files_to_convert:
            return self.to_m4a_filename(in_file)
        else:
            return in_file
    
    def calc_target_paths_for(self, l, files_to_convert):
        return [self.to_target_dir(self.get_outfile_for(f, files_to_convert))
                for f in l]

    def calc_dirs_to_create(self, subdirs):
        all_dirs = [x for x in map(self.to_target_dir, subdirs)
                + [self.temp_dir]]
        return [x for x in all_dirs if not os.path.isdir(x)]

    def calc_intermediate_files(self, num):
        return [os.path.join(self.temp_dir, 'intermediate%d.caf' % id_number)
                for id_number in range(num)]

    def calc_new_music_files(self, music_files):
        unconverted_targets = [self.to_target_dir(f) for f in music_files]
        converted_targets = [self.to_target_dir(self.to_m4a_filename(f))
                for f in music_files]
        # files that already an existing unconverted or converted target
        # are ignored.
        return [f[0] for f in
            zip(music_files, unconverted_targets, converted_targets)
            if not any((os.path.exists(x) for x in f[1:]))]


if __name__ == '__main__':

    path_calc = PathCalcualtor()
    music_files, subdirs = path_calc.analyze_directory_structure()
  
    # files that seem to have been added to the library since the last run
    new_music_files = path_calc.calc_new_music_files(music_files)

    results = map_to_pool(needs_converting, new_music_files)
    
    files_to_convert = [f[1] for f in zip(results, new_music_files) if f[0]]
    files_to_copy = [f for f in new_music_files if not f in files_to_convert]
   
    dirs_to_create = path_calc.calc_dirs_to_create(subdirs)
    [makedirs(d) for d in dirs_to_create]

    # TODO: one might want to extract a method/function from here on...
    copy_targets = path_calc.calc_target_paths_for(
            files_to_copy, files_to_convert)
    [copy(*p) for p in zip(files_to_copy, copy_targets)]

    intermediate_files = path_calc.calc_intermediate_files(
            len(files_to_convert))
    conversion_targets = path_calc.calc_target_paths_for(
            files_to_convert, files_to_convert)
    results = map_to_pool(convert_files_l,
            zip(files_to_convert, conversion_targets, intermediate_files))
    
    print('%d files copied - %d files converted.'
            %(len(files_to_copy), len(files_to_convert)))
    if any(results):
        print('Errors occured:')
        [print(e) for e in results if e]

