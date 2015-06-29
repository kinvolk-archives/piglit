# Copyright (c) 2015 Intel Corporation

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Tests for compressed backends.

This modules tests for compression support. Most of the tests are fairly basic,
aiming to verify that compression and decompression works as expected.

"""

from __future__ import print_function, absolute_import, division
import os
import functools

import nose.tools as nt

from framework.tests import utils
from framework.backends import compression, abstract

# pylint: disable=line-too-long,protected-access

# Helpers


class _TestBackend(abstract.FileBackend):
    """A class for testing backend compression."""
    _file_extension = 'test_extension'

    def initialize(self, *args, **kwargs):  # pylint: disable=unused-argument
        os.mkdir(os.path.join(self._dest, 'tests'))

    def finalize(self, *args, **kwargs): # pylint: disable=unused-argument
        tests = os.path.join(self._dest, 'tests')
        with self._write_final(os.path.join(self._dest, 'results.txt')) as f:
            for file_ in os.listdir(tests):
                with open(os.path.join(tests, file_), 'r') as t:
                    f.write(t.read())

    @staticmethod
    def _write(f, name, data):  # pylint: disable=arguments-differ
        f.write('{}: {}'.format(name, data))


def _add_compression(value):
    """Decorator that temporarily adds support for a compression method."""

    def _wrapper(func):
        """The actual wrapper."""

        @functools.wraps(func)
        def _inner(*args, **kwargs):
            """The function called."""
            compression.COMPRESSORS[value] = None
            compression.DECOMPRESSORS[value] = None

            try:
                func(*args, **kwargs)
            finally:
                del compression.COMPRESSORS[value]
                del compression.DECOMPRESSORS[value]

        return _inner

    return _wrapper


def _set_compression_mode(mode):
    """Change the compression mode for one test."""

    def _wrapper(func):
        """The actual decorator."""

        @functools.wraps(func)
        @utils.set_env(PIGLIT_COMPRESSION=mode)
        def _inner(*args, **kwargs):
            """The called function."""
            restore = compression.MODE
            compression.MODE = compression._set_mode()
            compression.COMPRESSOR = compression.COMPRESSORS[compression.MODE]

            try:
                func(*args, **kwargs)
            finally:
                compression.MODE = restore
                compression.COMPRESSOR = compression.COMPRESSORS[compression.MODE]

        return _inner

    return _wrapper


def _test_compressor(mode):
    """Helper to simplify testing compressors."""
    func = compression.COMPRESSORS[mode]
    with utils.tempdir() as t:
        with func(os.path.join(t, 'file')) as f:
            f.write('foo')


def _test_decompressor(mode):
    """helper to simplify testing decompressors."""
    func = compression.COMPRESSORS[mode]
    dec = compression.DECOMPRESSORS[mode]

    with utils.tempdir() as t:
        path = os.path.join(t, 'file')

        with func(path) as f:
            f.write('foo')

        with dec(path) as f:
            nt.eq_(f.read(), 'foo')


def _test_extension():
    """Create an final file and return the extension."""
    with utils.tempdir() as d:
        obj = _TestBackend(d)
        obj.initialize()
        with obj.write_test('foo') as t:
            t({'result': 'foo'})

        obj.finalize()

        for each in os.listdir(d):
            if each.startswith('results.txt'):
                ext = os.path.splitext(each)[1]
                break
        else:
            raise utils.TestFailure('No results file generated')

    return ext


# Tests


@utils.no_error
def test_compress_none():
    """framework.backends.compression: can compress to 'none'"""
    _test_compressor('none')


def test_decompress_none():
    """framework.backends.compression: can decompress from 'none'"""
    _test_decompressor('none')



@_add_compression('foobar')
@utils.set_env(PIGLIT_COMPRESSION='foobar')
def test_set_mode_env():
    """framework.backends.compression._set_mode: uses PIGlIT_COMPRESSION environment variable"""
    nt.eq_(compression._set_mode(), 'foobar')


@_add_compression('foobar')
@utils.set_env(PIGLIT_COMPRESSION=None)
@utils.set_piglit_conf(('core', 'compression', 'foobar'))
def test_set_mode_piglit_conf():
    """framework.backends.compression._set_mode: uses piglit.conf [core]:compression value if env is unset"""
    nt.eq_(compression._set_mode(), 'foobar')


@utils.set_env(PIGLIT_COMPRESSION=None)
@utils.set_piglit_conf(('core', 'compression', None))
def test_set_mode_default():
    """framework.backends.compression._set_mode: uses DEFAULT if env and piglit.conf are unset"""
    nt.eq_(compression._set_mode(), compression.DEFAULT)


@utils.no_error
def test_compress_gz():
    """framework.backends.compression: can compress to 'gz'"""
    _test_compressor('gz')


def test_decompress_gz():
    """framework.backends.compression: can decompress from 'gz'"""
    _test_decompressor('gz')


@_set_compression_mode('gz')
def test_gz_output():
    """framework.backends: when using gz compression a gz file is created"""
    nt.eq_(_test_extension(), '.gz')