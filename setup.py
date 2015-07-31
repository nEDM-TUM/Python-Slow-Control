from setuptools import setup, find_packages

setup(
  name='pynedm',
  version='0.0.14',
  packages=['pynedm'],
  url='https://github.com/nEDM-TUM/Python-Slow-Control',
  author='Michael Marino',
  author_email='mmarino@gmail.com',
  install_requires=['cloudant', 'pycurl']
)
