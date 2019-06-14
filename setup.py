from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='espy',
    version='0.1',
    description='Python API for ESP-r',
    author='John Allison',
    author_email='',
    packages=['espy'],  #same as name
    install_requires=['datetime', 'numpy', 'matplotlib'], #external packages as dependencies
)