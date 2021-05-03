#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

version = {}
with open(os.path.join(here, 'perfectfit', '__version__.py')) as f:
    exec(f.read(), version)

with open('requirements.txt', mode='r') as f:
    install_requires = f.read().splitlines()

with open('README.md') as readme_file:
    readme = readme_file.read()

setup(
    name='perfectfit',
    version=version['__version__'],
    description="Python implementation of PerfectFit API",
    long_description=readme + '\n\n',
    long_description_content_type='text/markdown',
    author='',
    author_email='',
    url='https://github.com/PerfectFit-project/virtual-coach-server',
    packages=find_packages(),
    include_package_data=True,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords=['PerfectFit'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    test_suite='tests',
    install_requires=install_requires,
    extras_require={
        'dev': ['prospector[with_pyroma]', 'yapf', 'isort'],
        'tests': ['pytest>5.0', 'pytest-cov', 'coveralls'],
        # 'docs': ['sphinx', 'sphinx_rtd_theme', 'recommonmark'],
    },
)
