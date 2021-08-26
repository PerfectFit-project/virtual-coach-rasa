import os
import io
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))

with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name = "rasa_bot", 
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: Apache-2.0",
        # supported python versions
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
    ],
    version = "0.1",
    description = "Virtual coach for Perfect Fit",
    long_description = long_description,
    author = "Perfect Fit",
    license="Apache-2.0",
    url="https://github.com/PerfectFit-project/virtual-coach-server/tree/main/Rasa_Bot",
    packages = find_packages(include=['actions', 'actions.*', 'tests', 'tests.*'])
    )
