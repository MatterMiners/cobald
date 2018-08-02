#!/usr/bin/env python
import os
from setuptools import setup, find_packages

repo_base_dir = os.path.abspath(os.path.dirname(__file__))
# pull in the packages metadata
package_about = {}
with open(os.path.join(repo_base_dir, "cobald", "__about__.py")) as about_file:
    exec(about_file.read(), package_about)


with open(os.path.join(repo_base_dir, 'README.rst'), 'r') as README:
    long_description = README.read()

if __name__ == '__main__':
    setup(
        name=package_about['__title__'],
        version=package_about['__version__'],
        description=package_about['__summary__'],
        long_description=long_description.strip(),
        author=package_about['__author__'],
        author_email=package_about['__email__'],
        url=package_about['__url__'],
        packages=find_packages(),
        entry_points={
            'console_scripts': [
                'cobald = cobald.daemon.core:main',
            ],
        },
        # dependencies
        install_requires=[
            'typing',
            'pyyaml',
            'trio',
            'include',
        ],
        extras_require={
            'docs':  ["sphinx", "sphinxcontrib-tikz"],
        },
        # metadata for package search
        license='MIT',
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        classifiers=[
            'Development Status :: 2 - Pre-Alpha',
            'Intended Audience :: Developers',
            'Intended Audience :: Information Technology',
            'Intended Audience :: Science/Research',
            'Intended Audience :: System Administrators',
            'Topic :: Adaptive Technologies',
            'Topic :: Office/Business :: Scheduling',
            'Topic :: System :: Distributed Computing',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
        ],
        keywords=package_about['__keywords__'],
        # unit tests
        setup_requires=['pytest-runner'],
        test_suite='cobald_tests',
        tests_require=['pytest'],
    )
