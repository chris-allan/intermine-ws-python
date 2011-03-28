The InterMine Python Webservice Client
=====================================

> An implementation of a webservice client 
> for InterMine webservices, written in Python

Who should use this software?
-----------------------------

This software is intended for people who make 
use of InterMine datawarehouses (ie. Biologists)
and who want a quicker, more automated way 
to perform queries. Some examples of sites that
are powered by InterMine software, and thus offer
a compatible webservice API are:

* FlyMine
* MetabolicMine
* modMine
* RatMine
* YeastMine

Queries here refer to database queries over the 
integrated datawarehouse. Instead of using 
SQL, InterMine services use a flexible and 
powerful sub-set of database query language
to enable wide-ranging and arbitrary queries.

Downloading:
------------

To download the client library, you will need to use git: 
You can download a copy of the libray with the following command

  git clone git://github.com/alexkalderimis/intermine-ws-python.git

This will download the source code to a directory called intermine-ws-python
in your current directory.

Running the Tests:
------------------

If you would like ot run the test suite, you can do so by executing
the following command: (from the source directory)

  python -m intermine.test.test

Installation:
-------------

Once downloaded, you can install the module with the command (from the source directory):

  python setup.py install

Further documentation:
----------------------

Please visit http://www.intermine.org/wiki/PythonClient for
further help and examples.

License:
--------

All InterMine code is freely available under the LGPL license: http://www.gnu.org/licenses/lgpl.html 


