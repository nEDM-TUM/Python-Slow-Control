from setuptools import setup, find_packages

setup(
  name='pynedm',
  version='0.1.0',
  packages=['pynedm'],
  url='https://github.com/nEDM-TUM/Python-Slow-Control',
  author='Michael Marino',
  author_email='mmarino@gmail.com',
  install_requires=[
    'cloudant==0.5.9-nedm',
    'pycurl',
    'autobahn',
    'netifaces',
    'twisted'
  ],
  dependency_links=[
    "https://github.com/nEDM-TUM/cloudant-python/tarball/nedm-version-0.5.9#egg=cloudant-0.5.9-nedm"
  ]

)
