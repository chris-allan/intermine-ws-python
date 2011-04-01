"""
The test and clean code is shamelessly stolen from
http://da44en.wordpress.com/2002/11/22/using-distutils/
"""

from distutils.core import Command, setup
from unittest import TextTestRunner, TestLoader
from glob import glob
from os.path import splitext, basename, join as pjoin, walk
from warnings import warn
import os

class TestCommand(Command):
    user_options = [ ]

    def initialize_options(self):
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        '''
        Finds all the tests modules in tests/, and runs them.
        '''
        testfiles = [ ]
        for t in glob(pjoin(self._dir, 'tests', '*.py')):
            if not t.endswith('__init__.py'):
                testfiles.append('.'.join(
                    ['tests', splitext(basename(t))[0]])
                )

        print testfiles
        tests = TestLoader().loadTestsFromNames(testfiles)
        t = TextTestRunner(verbosity = 1)
        t.run(tests)

class CleanCommand(Command):
    """
    Remove all build files and all compiled files
    =============================================

    Remove everything from build, including that 
    directory, and all .pyc files
    """
    user_options = [ ]

    def initialize_options(self):
        self._files_to_delete = [ ]
        self._dirs_to_delete = [ ]

        for root, dirs, files in os.walk('.'):
            for f in files:
                if f.endswith('.pyc'):
                    self._files_to_delete.append(pjoin(root, f))
        for root, dirs, files in os.walk(pjoin('build')):
            for f in files:
                self._files_to_delete.append(pjoin(root, f))
            for d in dirs:
                self._dirs_to_delete.append(pjoin(root, d))
        # reverse dir list to only get empty dirs
        self._dirs_to_delete.reverse()
        self._dirs_to_delete.append('build')

    def finalize_options(self):
        pass

    def run(self):
        for clean_me in self._files_to_delete:
            try:
                os.unlink(clean_me)
            except Exception as e:
                message = " ".join(["Failed to delete file", clean_me, str(e)])
                warn(message)
        for clean_me in self._dirs_to_delete:
            try:
                os.rmdir(clean_me)
            except Exception as e:
                message = " ".join(["Failed to delete dir", clean_me, str(e)])
                warn(message)

setup(
        name = "intermine",
        packages = ["intermine"],
        cmdclass = { 'test': TestCommand, 'clean': CleanCommand },
        version = "0.96.00",
        description = "InterMine WebService client",
        author = "Alex Kalderimis",
        author_email = "dev@intermine.org",
        url = "http://www.intermine.org/",
        download_url = "http://www.intermine.org/lib/python-webservice-client-0.96.00.tar.gz",
        keywords = ["webservice", "genomic", "bioinformatics"],
        classifiers = [
            "Programming Language :: Python",
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Science/Research",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Scientific/Engineering :: Bio-Informatics",
            "Topic :: Scientific/Engineering :: Information Analysis",
            "Operating System :: OS Independent",
            ],
        license = "LGPL",
        long_description = """\
InterMine Webservice Client
----------------------------

Provides access routines to datawarehouses powered 
by InterMine technology.

""",
)
