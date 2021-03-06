Changelog
=========

1.1.3
-----
  * New class BackendDiff
  * clean_mmt with more helper code for finding/cleaning overlapping activities
  * Backend: rename copy_all_from to sync_from and add parameters
  * hide class Authenticate from public API
  * Define assumption about points having to be ordered by time
  * Do not use slow GPX.get_time_bounds()
  * Activity.last_time now is a property
  * MMT: Map Activity.keywords to MMT tags
  * Activity.keywords now returns them sorted
  * MMT: login only once per backend instance

1.1.2  release 2017-03-4
------------------------
  * a first example
  * simplify authentication
  * simplify Backend API
  * len(backend) is the number of activities
  * Allow backend[x] and x in backend
  * hide Backend.activities, directly add needed methods to Backend
  * MMT: Download activity sometimes did not download the entire track
  * bin/test and bin/coverage now accept test method names (without `test_` prefix)
  * Directory: removes dead links without raising an exception
  * Activity.description never returns None
  * Activity: Parsing illegal GPX XML now prints a more helpful error message
  * Activity.clone() first does load_full
  * Activity(gpx=gpx) now handles keywords correctly
  * Backend.save() now accepts ident=str
  * Directory tries not to use illegal file names for symlinks

1.1.1  released 2017-02-26
--------------------------
  * Added Changelog

1.1.0  released 2017-02-26 
--------------------------
  * New backend ServerDirectory

1.0.1  released 2017-02-25
--------------------------
  * Documentation fixes

1.0.0  released 2017-02-25
--------------------------
  * Initial version supporting backends Directory and MMT



