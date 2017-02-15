Gpxmove is a Python - library making it easy to move activities between different backends.
In this context, a backend is a place where activities can be stored.

Implemented backends are:

  * :class:`~gpxmove.backends.directory`: Directory for .gpx files on an accessible file system: 
  * :class:`~gpxmove.backends.mmt`: For activities on http://mapmytracks.com

Some backends do not support everything we would like to have, you might get the
exception NotImplementedError(). Some backends simply do not offer everything we
want.

Sometimes Gpxmove uses undocumented ways to access a backend - this is done
when there is no documented way or when the official API implementation is
buggy or too slow for real-life use.

Backends might change their behaviour, and Gxpmove will have to be updated.

Gpxmove supports unicode characters, encoding them as UTF-8. All non-unicode
character sets like ISO8859-1 are considered obsolete. They may work or not.
Do not report bugs about those, I will not fix that.