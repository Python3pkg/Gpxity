#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) Wolfgang Rohdewald <wolfgang@rohdewald.de>
# See LICENSE for details.

"""
This module defines :class:`~gpxity.Activity`
"""

from math import asin, sqrt, degrees
import datetime
from contextlib import contextmanager


import gpxpy
from gpxpy.gpx import GPX, GPXTrack, GPXTrackSegment



__all__ = ['Activity']


class Activity:

    """Represents an activity.

    An activity is essentially a GPX file. If a backend supports attributes not directly
    supported by the GPX format like the MapMyTracks activity type, they will
    transparently be encodeded in existing GPX fields like keywords, see :class:`~gpxity.activity.Activity`.

    If an activity is assigned to a backend, all changes will be written directly to the backend.

    You can use the context manager :meth:`batch_changes`. This holds back updating the backend until
    the context is exiting.

    Not all backends support everything, you could get the exception NotImplementedError.


    Args:
        backend (Backend): The Backend where this Activity lives in. If
            it was constructed in memory, backend is None. backend will not be modifiable, even
            if initialized as None.
            Instead, use :literal:`new_activity = backend.save(activity)`.
        gpx (GPX): Initial content.

    At least one of **backend** or **gpx** must be None.

    Attributes:
        legal_what (tuple(str)): The legal values for :attr:`~Activity.what`. The first one is used
            as default value.
        id_in_backend (str): Every backend has its own scheme for unique activity ids.
        loading (bool): True while the activity loads from backend. Do not change this unless
            you implement a new backend.

    Todo:
        loading: make that a context manager

    """

    # pylint: disable = too-many-instance-attributes

    legal_what = (
        'Cycling', 'Running', 'Mountain biking', 'Indoor cycling', 'Sailing', 'Walking', 'Hiking',
        'Swimming', 'Driving', 'Off road driving', 'Motor racing', 'Motorcycling', 'Enduro',
        'Skiing', 'Cross country skiing', 'Canoeing', 'Kayaking', 'Sea kayaking', 'Stand up paddle boarding',
        'Rowing', 'Windsurfing', 'Kiteboarding', 'Orienteering', 'Mountaineering', 'Skating',
        'Skateboarding', 'Horse riding', 'Hang gliding', 'Gliding', 'Flying', 'Snowboarding',
        'Paragliding', 'Hot air ballooning', 'Nordic walking', 'Snowshoeing', 'Jet skiing', 'Powerboating',
        'Miscellaneous')

    def __init__(self, backend=None, id_in_backend: str=None, gpx=None):
        self.loading = False
        self._loaded = backend is None
        self._batch_changes = False
        self.__what = self.legal_what[0]
        self.__public = False
        self.id_in_backend = id_in_backend
        self.__gpx = gpx or GPX()
        self.__backend = None
        if backend is not None:
            if gpx is not None:
                raise Exception('Cannot accept backend and gpx')
        self.__backend = backend
        if backend and self not in backend.activities:
            backend.activities.append(self)

    @property
    def backend(self):
        """The backend this activity lives in.
        If you change it from None to a backend, this activity is automatically saved in that backend.

        It is not possible to decouple an activity from its backend, use :meth:`~gpxity.activity.Activity.clone()`.

        It is not possible to move the activity to a different backend by changing this.
        Use :meth:`Backend.save() <gpxity.backend.Backend.save()>` instead.
        """
        return self.__backend

    @backend.setter
    def backend(self, value):
        """TODO: a in backend, b=a.clone(), b in dasselbe backend setzen. Sollte nicht gehen."""
        if value is not self.__backend:
            if value is None:
                raise Exception('You cannot decouple an activity from its backend. Use clone().')
            elif self.__backend is not None:
                raise Exception(
                    'You cannot assign the activity to a different backend this way. '
                    'Please use Backend.save(activity).')
            else:
                self.__backend = value
                self.__backend.save(self)

    def clone(self):
        """Create a new activity with the same content but without backend

        Returns:
            the new activity
        """
        result = Activity(gpx=self.__gpx.clone())
        result.what = self.what
        result.public = self.public
        return result

    def save(self):
        """save this activity in the associated backend."""
        if not self.backend:
            raise Exception('Please assign a backend before saving')
        self.backend.save(self)

    @property
    def time(self) ->datetime.datetime:
        """datetime.datetime: start time of activity.
        If gpx.time is undefined, use the first time from track points."""
        if not self.__gpx.time:
            self.__gpx.time = self.__gpx.get_time_bounds()[0]
        return self.__gpx.time

    @time.setter
    def time(self, value: datetime.datetime):
        if value != self.time:
            self.__gpx.time = value

    def adjust_time(self):
        """set gpx.time to the time of the first trackpoint.
        We must do this for mapmytracks because it does
        not support uploading the time, it computes the time
        from the first trackpoint. We want to be synchronous."""
        self._load_full()
        self.__gpx.time = self.__gpx.get_time_bounds()[0]

    @property
    def title(self) -> str:
        """str: The title. Internally stored in gpx.title, but every backend
            may actually store this differently. But this is transparent to the user.
        """
        return self.__gpx.name

    @title.setter
    def title(self, value: str):
        if value != self.__gpx.name:
            self.__gpx.name = value
            if self.write_direct():
                self.backend.change_title(self)

    @property
    def description(self) ->str:
        """str: The description. Internally stored in gpx.description, but every backend
            may actually store this differently. But this is transparent to the user.
        """
        return self.__gpx.description

    @contextmanager
    def batch_changes(self):
        """This context manager disables  the direct update in the backend
        and saves the entire activity when done.
        """
        prev_batch_changes = self._batch_changes
        self._batch_changes = True
        yield
        self._batch_changes = prev_batch_changes
        if self.write_direct():
            self.save()

    def write_direct(self):
        """True if changes are applied directly to the backend
        which is default. False if:
        - we are currently loading from backend: Avoid recursion
        - _batch_changes is active
        - we have no backend
        """
        return self.backend and not self.loading and not self._batch_changes

    @description.setter
    def description(self, value: str):
        if value != self.__gpx.description:
            self.__gpx.description = value
            if self.write_direct():
                self.backend.change_description(self)

    @property
    def what(self) ->str:
        """str: What is this activity doing? If we have no current value,
        return the default.

        Returns:
            The current value or the default value (see `legal_what`)
        """
        return self.__what

    @what.setter
    def what(self, value: str):
        if value != self.__what:
            if value not in Activity.legal_what and value is not None:
                raise Exception('What {} is not known'.format(value))
            self.__what = value if value else self.legal_what[0]
            if self.write_direct():
                self.backend.change_what(self)

    def point_count(self) ->int:
        """
        Returns:
          total count over all tracks and segments"""
        self._load_full()
        result = 0
        for track in self.__gpx.tracks:
            for segment in track.segments:
                result += len(segment.points)
        return result

    def _load_full(self) ->None:
        """load the full track from source_backend if not yet loaded."""
        if self.backend and not self._loaded and not self.loading:
            self.backend.load_full(self)

    def add_points(self, points) ->None:
        """adds points to last segment in the last track. If no track
        is allocated yet, do so.

        UNFINISHED

        Args:
            points (list(GPXTrackPoint): The points to be added
        """
        if self.__gpx.tracks:
            # make sure the same points are not added twice
            assert points != self.__gpx.tracks[-1].segments[-1].points[-len(points):]
        self._load_full()
        if not self.__gpx.tracks:
            self.__gpx.tracks.append(GPXTrack())
            self.__gpx.tracks[0].segments.append(GPXTrackSegment())
        self.__gpx.tracks[-1].segments[-1].points.extend(points)

    def _parse_keywords(self):
        """self.keywords is 1:1 as parsed from xml. Here we extract
        our special keywords What: and Status:"""
        new_keywords = list()
        for keyword in self.keywords:
            if keyword.startswith('What:'):
                self.what = keyword.split(':')[1]
            elif keyword.startswith('Status:'):
                self.public = keyword.split(':')[1] == 'public'
            else:
                new_keywords.append(keyword)
        self.keywords = new_keywords

    def parse(self, indata):
        """parse GPX.
        title, description and what from indata have precedence.
        public will be or-ed

        Args:
            indata: may be a file descriptor or str
        """
        if hasattr(indata, 'read'):
            indata = indata.read()
        if not indata:
            # ignore empty file
            return
        is_loading = self.loading
        self.loading = True
        try:
            old_gpx = self.__gpx
            old_public = self.public
            self.__gpx = gpxpy.parse(indata)
            self._parse_keywords()
            self.public = self.public or old_public
            if old_gpx.name and not self.__gpx.name:
                self.__gpx.name = old_gpx.name
            if old_gpx.description and not self.__gpx.description:
                self.__gpx.description = old_gpx.description
            self._loaded = True
        finally:
            self.loading = is_loading

    def to_xml(self) ->str:
        """Produce exactly one line per trackpoint for easier editing
        (like removal of unwanted points).
        """
        self._load_full()
        new_keywords = self.keywords
        new_keywords.append('What:{}'.format(self.what))
        if self.public:
            new_keywords.append('Status:public')
        old_keywords = self.__gpx.keywords
        try:
            self.__gpx.keywords = ', '.join(new_keywords)

            result = self.__gpx.to_xml()
            result = result.replace('</trkpt><', '</trkpt>\n<')
            result = result.replace('<link ></link>', '')   # and remove those empty <link> tags
            result = result.replace('\n</trkpt>', '</trkpt>')
            result = result.replace('\n\n', '\n')
        finally:
            self.__gpx.keywords = old_keywords
        return result

    @property
    def public(self):
        """
        bool: Is this a private activity (can only be seen by the account holder) or
            is it public?
        """
        return self.__public

    @public.setter
    def public(self, value):
        """stores this flag as keyword 'public'"""
        if value != self.public:
            self.__public = value
            if self.write_direct():
                self.backend.change_public(self)

    @property
    def gpx(self) ->GPX:
        """
        Direct access to the GPX object.If you use it to change its content,
        remember to save the activity.
        Returns:
            the GPX object, readonly.
        """
        self._load_full()
        return self.__gpx

    def last_time(self) ->datetime.datetime:
        """
        Returns:
            the last timestamp we received so far"""
        self._load_full()
        return self.__gpx.get_time_bounds().end_time

    @property
    def keywords(self):
        """list(str): represent them as a list - in GPX they are comma separated.
            Content is whatever you want.

            Because the GPX format does not have attributes for everything used by all backends,
            we encode some of the backend arguments in keywords.

            Example for mapmytracks: keywords = 'Status:public, What:Cycling'.

            However this is transparent for you. When parsing the XML, those are removed
            from keywords, and the are re-added in Activity.to_xml().
        """
        self._load_full()
        if self.__gpx.keywords:
            return list(x.strip() for x in self.__gpx.keywords.split(','))
        else:
            return list()

    @keywords.setter
    def keywords(self, value):
        """replace all keywords with a new list.

        Args:
            value (list(str)): a list of keywords
        """
        with self.batch_changes():
            self.__gpx.keywords = ''
            for keyword in value:
                # add_keyword ensures we do not get unwanted things like What:
                self.add_keyword(keyword)

    @staticmethod
    def _check_keyword(keyword):
        """must not be What: or Status:"""
        if keyword.startswith('What:'):
            raise Exception('Do not use this directly,  use Activity.what')
        if keyword.startswith('Status:'):
            raise Exception('Do not use this directly,  use Activity.public')

    def add_keyword(self, value: str) ->None:
        """adds to the comma separated keywords. Duplicate keywords are forbidden.

        Args:
            value: the keyword
        """
        self._check_keyword(value)
        self._load_full()
        if value in self.keywords:
            raise Exception('Keywords may not be duplicate: {}'.format(value))
        if self.__gpx.keywords:
            self.__gpx.keywords += ', {}'.format(value)
        else:
            self.__gpx.keywords = value
        if self.write_direct():
            self.save()

    def remove_keyword(self, value: str) ->None:
        """removes from the keywords.

        Args:
            value: the keyword to be removed
        """
        self._check_keyword(value)
        self._load_full()
        self.__gpx.keywords = ', '.join(x for x in self.keywords if x != value)
        if self.write_direct():
            self.save()

    def __repr__(self):
        parts = []
        if self.backend:
            parts.append(repr(self.backend))
            parts.append(' id:{}'.format(self.id_in_backend))
        if self.__gpx:
            parts.append(self.what)
            if self.__gpx.name:
                parts.append(self.__gpx.name)
            if self.__gpx.get_time_bounds()[0]:
                parts.append('{}-{}'.format(*self.__gpx.get_time_bounds()))
            parts.append('{} points'.format(self.point_count()))
            if self.angle():
                parts.append('angle={}'.format(self.angle()))
        return 'Activity({})'.format(' '.join(parts))

    def __str__(self):
        return self.__repr__()

    def key(self) ->str:
        """for speed optimized equality checks, not granted to be exact

        Returns:
            a string with selected attributes in printable form
        """
        self._load_full()
        return 'title:{} description:{} keywords:{} what{}: public:{} last_time:{} angle:{} points:{}'.format(
            self.title, self.description,
            ','.join(self.keywords), self.what, self.public, self.last_time(), self.angle(), self.point_count())

    def angle(self) ->float:
        """For me, the earth is flat.

        Returns:
            the angle in degrees 0..360 between start and end.
            If we have no track, return 0
        """
        self._load_full()
        if not self.__gpx.tracks:
            return 0
        first_point = self.__gpx.tracks[0].segments[0].points[0]
        last_point = self.__gpx.tracks[-1].segments[-1].points[-1]
        delta_lat = first_point.latitude - last_point.latitude
        delta_long = first_point.longitude - last_point.longitude
        norm_lat = delta_lat / 90.0
        norm_long = delta_long / 180.0
        try:
            result = int(degrees(asin(norm_long / sqrt(norm_lat**2 + norm_long **2))))
        except ZeroDivisionError:
            return 0
        if norm_lat >= 0.0:
            return (360.0 + result) % 360.0
        else:
            return 180.0 - result

    def all_points(self):
        """
        First, this fully loads the activity if not yet done.

        Yields:
            GPXTrackPoint: all points in all tracks and segments
        """
        self._load_full()
        for track in self.__gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    yield point

    def points_equal(self, other, verbose=False) ->bool:
        """
        First, this fully loads the activity if not yet done.

        Returns:
            True if both have identical points. All points of all tracks and segments are combined.
        """
        self._load_full()
        if self.point_count() != other.point_count():
            if verbose:
                print('Activities {} and {} have different # of points'.format(self, other))
            return False
        if self.angle() != other.angle():
            if verbose:
                print('Activities {} and {} have different angle'.format(self, other))
            return False
        for idx, (point1, point2) in enumerate(zip(self.all_points(), other.all_points())):
            # GPXTrackPoint has no __eq__ and no working hash()
            # those are only the most important attributes:
            if point1.longitude != point2.longitude:
                if verbose:
                    print('{} and {}: Points #{} have different longitude: {}, {}'.format(
                        self, other, idx, point1, point2))
                return False
            if point1.latitude != point2.latitude:
                if verbose:
                    print('{} and {}: Points #{} have different latitude: {}, {}'.format(
                        self, other, idx, point1, point2))
                return False
            if point1.elevation != point2.elevation:
                if verbose:
                    print('{} and {}: Points #{} have different elevation: {}, {}'.format(
                        self, other, idx, point1, point2))
                return False
        return True
