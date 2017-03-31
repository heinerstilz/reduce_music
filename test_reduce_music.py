#!/usr/bin/python2
# test_reduce_music.py
#
# Heiner Stilz 2015
# heinerstilz@gmail.com

import os
import reduce_music
import unittest

class PathCalculatorTestFixture(unittest.TestCase):
    
    def setUp(self):
        self.path_calc = reduce_music.PathCalcualtor()


class PathCalculatorTargetExtensionTest(PathCalculatorTestFixture):

    def test(self):
        target_filename = self.path_calc.to_m4a_filename('foo.bar')
        self.failUnlessEqual('foo.m4a', target_filename)
        target_filename = self.path_calc.to_m4a_filename('foo/baz.bar')
        self.failUnlessEqual('foo/baz.m4a', target_filename)


class PathCalculatorTargetPathTest(PathCalculatorTestFixture):

    def test(self):
        target_path = self.path_calc.to_target_dir('baz.m4a')
        self.failUnlessEqual(os.path.join(self.path_calc.target_dir, 'baz.m4a'),
            target_path)


class PathCalculatorGetOutfileTest(PathCalculatorTestFixture):

    def test(self):
        try:
            self.path_calc.get_outfile_for('foo.bar', [])
            self.fail('Expected NotAMusicFileException.')
        except reduce_music.NotAMusicFileException:
            pass

        out_file = self.path_calc.get_outfile_for('foo.mp3', ['bar.mp3'])
        self.failUnlessEqual('foo.mp3', out_file)

        out_file = self.path_calc.get_outfile_for('bar.mp3', ['bar.mp3'])
        self.failUnlessEqual('bar.m4a', out_file)


class PathCalculatorGetTargetOutfilesTest(PathCalculatorTestFixture):

    def test(self):
        target_outf = self.path_calc.calc_target_paths_for(
                ['foo.mp3', 'bar.mp3'], ['bar.mp3'])
        self.failUnless(os.path.join(self.path_calc.target_dir, 'bar.m4a')
                in target_outf)
        self.failUnless(os.path.join(self.path_calc.target_dir, 'foo.mp3')
                in target_outf)
        self.failUnlessEqual(2, len(target_outf)) 
        self.failUnlessEqual(2, 3) 


class PathCalculatorGetintermediateFilesTest(PathCalculatorTestFixture):

    def test(self):
        intermediate_files = self.path_calc.calc_intermediate_files(4)
        self.failUnlessEqual(4, len(intermediate_files))
        self.failUnlessEqual(os.path.join(self.path_calc.temp_dir,
            'intermediate0.caf'), intermediate_files[0])
        self.failUnlessEqual(os.path.join(self.path_calc.temp_dir,
            'intermediate3.caf'), intermediate_files[-1])


if __name__ == '__main__':
    unittest.main()


