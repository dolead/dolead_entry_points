#!/usr/bin/env python3
from setuptools import setup


with open('README.md') as fd:
    readme = fd.read()

setup(name='dolead_entry_points',
      version='0.0.2',
      description='Multiple entry points generator',
      long_description=readme,
      keywords='flask celery web',
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"],
      license="GPLv3",
      author="François Schmidts",
      author_email="francois.schmidts@dolead.com",
      maintainer="François Schmidts",
      maintainer_email="francois.schmidts@dolead.com",
      packages=['dolead_entry_points'],
      url='https://github.com/dolead/dolead_entry_points',
      install_requires=['requests==2.13.0', 'celery==3.1.17'],
      )
