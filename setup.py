from setuptools import setup, find_packages

setup(
  name='pynedm',
  version='0.0.1.dev1',
  packages=find_packages('src'),
  package_dir = {'':'src'},
  url='https://github.com/nEDM-TUM/Python-Slow-Control',
  author='Michael Marino',
  author_email='mmarino@gmail.com',
  install_requires=['cloudant']
)
