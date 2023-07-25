#!/usr/bin/env python3

import os, re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

if __name__ == "__main__":

    setup(
        name = 'better_kerchunk',
        version = '0.0.1',
        description = 'Better Kerchunk',
        long_description = README,
        classifiers = [],
        author = 'Daniel Westwood',
        author_email = 'daniel.westwood@stfc.ac.uk',
        url = 'https://github.com/cedadev/better_kerchunk',
        keywords = '',
        packages = find_packages(),
        include_package_data = True,
        zip_safe = False,
        install_requires = [],
    )