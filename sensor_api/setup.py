from setuptools import setup

setup(
    name='sensor_api',
    version='0.1',
    author='Walter Baccinelli, Robin Richardson, Sven van den Burg, Bouke Scheltinga, Nele Albers',
    author_email='w.baccinelli@esciencecenter.nl',
    keywords=['PerfectFit', 'sensors data'],
    url='https://github.com/PerfectFit-project',
    # pylint: disable=consider-using-with, unspecified-encoding
    install_requires=open("requirements.txt", "r").readlines(),
    # pylint: disable=consider-using-with, unspecified-encoding
    long_description=open("README.md", "r").read(),
    long_description_content_type='text/markdown',
    packages=['sensorapi'],
    package_dir = {
        'sensorapii': './sensorapi',
    },
    include_package_data=True,
    description="Virtual Coach database python package",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License",
    ],
    python_requires=">= 3.8"
)
