#! /usr/bin/env python3

import os
import re
import sys
import sysconfig
import platform
import subprocess

from distutils.version import LooseVersion
from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext
from setuptools.command.test import test as TestCommand


class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=''):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    def run(self):
        try:
            out = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: " +
                ", ".join(e.name for e in self.extensions))

        if platform.system() == "Windows":
            cmake_version = LooseVersion(re.search(r'version\s*([\d.]+)',
                                                   out.decode()).group(1))
            if cmake_version < '3.1.0':
                raise RuntimeError("CMake >= 3.1.0 is required on Windows")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(
            os.path.dirname(self.get_ext_fullpath(ext.name)))
        cmake_args = ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                      '-DPYTHON_EXECUTABLE=' + sys.executable]

        cfg = 'Debug' if self.debug else 'Release'
        build_args = ['--config', cfg]

        if platform.system() == "Windows":
            cmake_args += ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(
                cfg.upper(),
                extdir)]
            if sys.maxsize > 2**32:
                cmake_args += ['-A', 'x64']
            build_args += ['--', '/m']
        else:
            cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
            build_args += ['--', '-j2']

        env = os.environ.copy()
        env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(
            env.get('CXXFLAGS', ''),
            self.distribution.get_version())
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        subprocess.check_call(['cmake', ext.sourcedir] + cmake_args,
                              cwd=self.build_temp, env=env)
        subprocess.check_call(['cmake', '--build', '.'] + build_args,
                              cwd=self.build_temp)
        print()  # Add an empty line for cleaner output


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

_VERSION = "0.1.0"

setup(
    name='pinetree',
    version=_VERSION,
    description='stochastic simulation of gene expression with site-specific translation rates',
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Benjamin Jack',
    author_email='benjamin.r.jack@gmail.com',
    url='https://github.com/benjaminjack/pinetree',
    download_url='https://github.com/benjaminjack/pinetree/archive/v' + _VERSION + '.tar.gz',
    license=license,
    keywords=['gene', 'codon', 'transcription',
              'translation', 'biology', 'stochastic'],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    ext_modules=[CMakeExtension('pinetree/core')],
    cmdclass=dict(build_ext=CMakeBuild),
    zip_safe=False,
    test_suite='tests',
    install_requires=['cmake']
)
