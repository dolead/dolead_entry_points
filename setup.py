#!/usr/bin/env python3
from setuptools import setup


setup(name='dolead_entry_points',
      version='0.0.4',
      description='Multiple entry points generator',
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
      install_requires=['requests==2.21.0',
                        'celery<4',
                        'threaded-context==1.0.0'],
      )
