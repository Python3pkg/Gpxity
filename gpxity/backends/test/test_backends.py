# -*- coding: utf-8 -*-

# Copyright (c) Wolfgang Rohdewald <wolfgang@rohdewald.de>
# See LICENSE for details.

"""
implements :class:`gpxpy.backends.test.test_backends.TestBackends` for all backends
"""

import os
import time
import datetime
import random
import tempfile

from unittest import skip

import requests

from .basic import BasicTest
from .. import Directory, MMT, ServerDirectory, TrackMMT
from ...auth import Authenticate
from ... import Activity

# pylint: disable=attribute-defined-outside-init


class TestBackends(BasicTest):
    """Are the :literal:`supported_` attributes set correctly?"""

    def test_supported(self):
        """Check values in supported for all backends"""
        expect_unsupported = dict()
        expect_unsupported[Directory] = set(['track'])
        expect_unsupported[ServerDirectory] = set(['track'])
        expect_unsupported[MMT] = set()
        expect_unsupported[TrackMMT] = set([
            'remove', '_write_attribute',
            '_write_title', '_write_description', '_write_public',
            '_write_what', '_write_keyword', '_write_add_keyword',
            '_write_remove_keyword'])
        for cls in self._find_backend_classes():
            with self.subTest(' {}'.format(cls.__name__)):
                self.assertTrue(cls.supported & expect_unsupported[cls] == set())

    def test_save_empty(self):
        """Save empty activity"""
        for cls in self._find_backend_classes():
            with self.subTest(' {}'.format(cls.__name__)):
                can_remove = 'remove' in cls.supported
                with self.temp_backend(cls, cleanup=can_remove, clear_first=can_remove) as backend:
                    activity = Activity()
                    if cls is MMT or cls is TrackMMT:
                        with self.assertRaises(Exception):
                            backend.save(activity)
                    else:
                        self.assertIsNotNone(backend.save(activity))

    def test_backend(self):
        """Manipulate backend"""
        activity = self.create_test_activity()
        with Directory(cleanup=True) as directory1:
            with Directory(cleanup=True) as directory2:
                saved = directory1.save(activity)
                self.assertEqual(saved.backend, directory1)
                activity.backend = directory1
                with self.assertRaises(Exception):
                    activity.backend = directory2
                with self.assertRaises(Exception):
                    activity.backend = None

    def test_open_wrong_auth(self):
        """Open backends with wrong password"""
        for cls in self._find_backend_classes():
            with self.subTest(' {}'.format(cls.__name__)):
                if issubclass(cls, Directory):
                    with self.temp_backend(cls, sub_name='wrong', cleanup=True):
                        pass
                else:
                    with self.assertRaises(requests.exceptions.HTTPError):
                        self.setup_backend(cls, sub_name='wrong')

    def test_z9_create_backend(self):
        """Test creation of a backend"""
        for cls in self._find_backend_classes():
            if 'remove' in cls.supported:
                with self.subTest(' {}'.format(cls.__name__)):
                    with self.temp_backend(cls, count=3, clear_first=True, cleanup=True) as backend:
                        self.assertEqual(len(backend), 3)
                        first_time = backend.get_time()
                        time.sleep(2)
                        second_time = backend.get_time()
                        total_seconds = (second_time - first_time).total_seconds()
                        self.assertTrue(1 < total_seconds < 4, 'Time difference should be {}, is {}-{}={}'.format(
                            2, second_time, first_time, second_time - first_time))

    def test_write_remote_attributes(self):
        """If we change title, description, public, what in activity, is the backend updated?"""
        for cls in self._find_backend_classes():
            if 'remove' in cls.supported:
                with self.subTest(' {}'.format(cls.__name__)):
                    with self.temp_backend(cls, count=1, clear_first=True, cleanup=True) as backend:
                        activity = backend[0]
                        first_public = activity.public
                        first_title = activity.title
                        first_description = activity.description
                        first_what = activity.what
                        activity.public = not activity.public
                        activity.title = 'A new title'
                        self.assertEqual(activity.title, 'A new title')
                        activity.description = 'A new description'
                        if activity.what == 'Cycling':
                            activity.what = 'Running'
                        else:
                            activity.what = 'Cycling'
                        # make sure there is no cache in the way
                        backend2 = self.clone_backend(backend)
                        activity2 = backend2[0]
                        self.assertEqualActivities(activity, activity2)
                        self.assertNotEqual(first_public, activity2.public)
                        self.assertNotEqual(first_title, activity2.title)
                        self.assertNotEqual(first_description, activity2.description)
                        self.assertNotEqual(first_what, activity2.what)

    @skip
    def test_zz_all_what(self):
        """can we up- and download all values for :attr:`Activity.what`?"""
        what_count = len(Activity.legal_what)
        backends = list(
            self.setup_backend(x, count=what_count, clear_first=True)
            for x in self._find_backend_classes() if 'remove' in x.supported)
        copies = list(self.clone_backend(x) for x in backends)
        try:
            first_backend = copies[0]
            for other in copies[1:]:
                self.assertSameActivities(first_backend, other)
        finally:
            for backend in copies:
                backend.destroy()
            for backend in backends:
                backend.destroy()

    def test_z2_keywords(self):
        """save and load keywords. For now, all test keywords
        start with uppercase, avoiding MMT problems"""
        kw_a = 'A'
        kw_b = 'Berlin'
        kw_c = 'CamelCase'
        kw_d = 'D' # self.unicode_string2

        for cls in self._find_backend_classes():
            if cls.__name__ == 'TrackMMT':
                continue
            with self.subTest(' {}'.format(cls.__name__)):
                is_mmt = cls.__name__ == 'MMT'
                with self.temp_backend(cls, clear_first=not is_mmt, cleanup=not is_mmt, sub_name='two') as backend:
                    if not backend:
                        continue
                    activity = backend[0]
                    activity.keywords = list()
                    self.assertEqual(activity.keywords, list())
                    activity.keywords = ([kw_a, kw_b, kw_c])
                    activity.remove_keyword(kw_b)
                    self.assertEqual(activity.keywords, ([kw_a, kw_c]))
                    with self.assertRaises(Exception):
                        activity.add_keyword('What:whatever')
                    activity.add_keyword(kw_d)
                    self.assertEqual(set(activity.keywords), set([kw_a, kw_c, kw_d]))
                    backend2 = self.clone_backend(backend)
                    activity2 = backend2[activity.id_in_backend]
                    activity2.remove_keyword(kw_d)
                    self.assertEqual(activity2.keywords, ([kw_a, kw_c]))
                    self.assertEqual(activity.keywords, ([kw_a, kw_c, kw_d]))
                    backend.scan()
                    self.assertEqual(activity.keywords, ([kw_a, kw_c, kw_d]))
                    self.assertEqual(backend[activity.id_in_backend].keywords, ([kw_a, kw_c]))
                    activity.remove_keyword(kw_a)
                    # this is tricky: The current implementation assumes that activity.keywords is
                    # current - which it is not. activity still thinks kw_d is there but it has been
                    # removed by somebody else. MMT has a work-around for removing activities which
                    # removes them all and re-adds all wanted. So we get kw_d back.
                    self.assertEqual(activity.keywords, ([kw_c, kw_d]))
                    #activity2.remove_keyword(kw_a)
                    activity.remove_keyword(kw_c)
                    activity.remove_keyword(kw_d)
                    backend.scan()
                    self.assertEqual(backend[0].keywords, list())

    def test_z_unicode(self):
        """Can we up- and download unicode characters in all text attributes?"""
        tstdescr = 'DESCRIPTION with ' + self.unicode_string1 + ' and ' + self.unicode_string2
        for cls in self._find_backend_classes():
            if 'remove' in cls.supported:
                with self.subTest(' {}'.format(cls.__name__)):
                    with self.temp_backend(cls, count=1, clear_first=True) as backend:
                        backend2 = self.clone_backend(backend)
                        activity = backend[0]
                        activity.title = 'Title ' + self.unicode_string1
                        backend2.scan() # because backend2 does not know about changes thru backend
                        activity2 = backend2[0]
                        # activity and activity2 may not be identical. If the original activity
                        # contains gpx xml data ignored by MMT, it will not be in activity2.
                        self.assertEqual(activity.title, activity2.title)
                        activity.description = tstdescr
                        self.assertEqual(activity.description, tstdescr)
                        backend2.scan()
                        self.assertEqual(backend2[0].description, tstdescr)
                        backend2.destroy()

    def test_change_points(self):
        """Can we change the points of a track?

        For MMT this means re-uploading and removing the previous instance, so this
        is not always as trivial as it should be."""

    def test_download_many(self):
        """Download many activities"""
        many = 150
        backend = self.setup_backend(MMT, count=many, cleanup=False, clear_first=False, sub_name='many')
        self.assertEqual(len(backend), many)

    def test_duplicate_title(self):
        """two activities having the same title"""
        for cls in self._find_backend_classes():
            if 'remove' in cls.supported:
                with self.subTest(' {}'.format(cls.__name__)):
                    with self.temp_backend(cls, count=2, clear_first=True) as backend:
                        backend[0].title = 'TITLE'
                        backend[1].title = 'TITLE'

    def test_private(self):
        """Up- and download private activities"""
        with self.temp_backend(Directory, count=5, cleanup=True, status=False) as local:
            activity = Activity(gpx=self._get_gpx_from_test_file('test2'))
            activity.public = False
            self.assertFalse(activity.public)
            local.save(activity)
            for cls in self._find_backend_classes():
                if 'remove' in cls.supported:
                    with self.subTest(' {}'.format(cls.__name__)):
                        with self.temp_backend(cls, clear_first=True, cleanup=True) as backend:
                            backend.sync_from(local)
                            for _ in backend:
                                self.assertFalse(_.public)
                            backend2 = self.clone_backend(backend)
                            with Directory(cleanup=True) as copy:
                                copy.sync_from(backend2)
                                self.assertSameActivities(local, copy)

    def test_sync(self):
        """sync_from"""
        with self.temp_backend(Directory, count=5, cleanup=True) as source:

            with self.temp_backend(Directory, count=4, cleanup=True) as sink:
                for _ in sink:
                    self.move_times(_, datetime.timedelta(hours=100))
                sink.sync_from(source)
                self.assertEqual(len(sink), 9)
                sink.sync_from(source, remove=True)
                self.assertSameActivities(source, sink)

    def test_scan(self):
        """some tests about Backend.scan()"""
        with self.temp_backend(Directory, count=5, cleanup=True) as source:
            backend2 = self.clone_backend(source)
            activity = self.create_test_activity()
            backend2.save(activity)
            self.assertEqual(len(backend2), 6)
            source.scan() # because it cannot know backend2 added something

    def test_sync_trackmmt(self):
        """sync from local to MMT"""
        with self.temp_backend(Directory, count=5, cleanup=True) as source:
            with TrackMMT(auth='test') as sink:
                prev_len = len(sink)
                for _ in sink:
                    self.move_times(_, datetime.timedelta(hours=-random.randrange(10000)))
                sink.sync_from(source)
                self.assertEqual(len(sink), prev_len + 5)

    def test_track(self):
        """test life tracking"""
        activity = self.create_test_activity()
        with TrackMMT(auth='test') as uplink:
            activity.track(uplink, self.some_random_points())
            new_id = activity.id_in_backend
            time.sleep(2)
            activity.track(points=self.some_random_points())
            activity.track()
            self.assertIn(new_id, uplink)

    def test_directory_dirty(self):
        """test gpx.dirty where id_in_backend is not the default. Currently
        activity.dirty = 'gpx' changes the file name which is wrong."""
        pass

    def test_directory(self):
        """directory creation/deletion"""
        with self.assertRaises(Exception):
            with Directory('url', prefix='x', cleanup=True):
                pass

        dir_a = Directory(cleanup=True)
        self.assertTrue(dir_a.is_temporary)
        a_url = dir_a.url
        self.assertTrue(os.path.exists(a_url))
        dir_a.destroy()
        self.assertFalse(os.path.exists(a_url))

        test_url = tempfile.mkdtemp() + '/'
        dir_b = Directory(url=test_url, cleanup=True)
        self.assertFalse(dir_b.is_temporary)
        self.assertTrue(dir_b.url == test_url)
        dir_b.destroy()
        self.assertTrue(os.path.exists(test_url))
        os.rmdir(test_url)

        dir_c = Directory(auth='urltest')
        auth_dir = Authenticate(Directory, 'urltest').url
        if not auth_dir.endswith('/'):
            auth_dir += '/'
        self.assertFalse(dir_c.is_temporary)
        self.assertTrue(dir_c.url == auth_dir)
        dir_c.destroy()
        self.assertTrue(os.path.exists(auth_dir))
        os.rmdir(auth_dir)
