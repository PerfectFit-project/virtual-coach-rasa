from setuptools import setup

setup(
    name='sensor_api',
    version='0.1',
    author='Robin Richardson, Sven van den Burg, Bouke Scheltinga, Nele Albers',
    install_requires=open("requirements.txt", "r").readlines(),
    long_description=open("README.md", "r").read(),
    long_description_content_type='text/markdown',
    packages=['sensorapi'],
    package_dir = {
        'sensorapii': './sensorapi',
    },
    include_package_data=True,
    description="Virtual Coach database python package",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
)
