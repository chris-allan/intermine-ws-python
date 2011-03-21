from distutils.core import setup
setup(
        name = "intermine",
        packages = ["intermine"],
        version = "0.94.00",
        description = "InterMine WebService client",
        author = "Alex Kalderimis",
        author_email = "dev@intermine.org",
        url = "http://www.intermine.org/",
        download_url = "http://www.intermine.org/downloads/python-webservice-client-0.94.00.tgz",
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
        long_description = """\
InterMine Webservice Client
----------------------------

Provides access routines to query webservices implementing 
InterMine datawarehouses.

""",
)
