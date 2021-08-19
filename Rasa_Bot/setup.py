import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

setup(
      name = "rasa_bot", classifiers = [],
    packages=find_packages(where="demo"))