from setuptools import setup, find_packages

setup(
  name='pynedm',
  version='0.1.0',
  packages=['pynedm'],
  url='https://github.com/nEDM-TUM/Python-Slow-Control',
  author='Michael Marino',
  author_email='mmarino@gmail.com',
  install_requires=['cloudant == 0.5.8', 'pycurl', 'autobahn', 'netifaces', 'twisted']
)
