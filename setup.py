from setuptools import setup

setup(
   name='espy',
   version='0.1',
   description='Python API for ESP-r',
   author='John Allison',
   packages=['espy'],  #same as name
   install_requires=['datetime', 'numpy', 'matplotlib'], #external packages as dependencies
)