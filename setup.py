from setuptools import setup, find_packages
from pip.req import parse_requirements

install_reqs = parse_requirements("requirements.txt")
reqs = [str(ir.req) for ir in install_reqs]

setup(
  name='pynedm',
  version='0.1.0',
  packages=['pynedm'],
  url='https://github.com/nEDM-TUM/Python-Slow-Control',
  author='Michael Marino',
  author_email='mmarino@gmail.com',
  install_requires=reqs
)
