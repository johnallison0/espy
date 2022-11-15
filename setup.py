"""Setup file for installing module."""
from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()  # pylint: disable=invalid-name,locally-disabled

setup(
    name='espy',
    version='0.1',
    description='Python API for ESP-r',
    author='John Allison',
    author_email='',
    packages=['espy'],  #same as name
    install_requires=[  # external package dependencies
        'datetime',
        'matplotlib',
        'numpy',
        'pandas',
        'vtk',
        'wand'
    ], 
)
