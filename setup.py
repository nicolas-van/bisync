#! /usr/bin/python
# -*- coding: utf-8 -*-
from distutils.core import setup
import os.path

setup(name='bisync',
      version='0.8.0',
      description='Bisync',
      author='Nicolas Vanhoren',
      author_email='nicolas.vanhoren@unknown.com',
      url='https://github.com/nicolas-van/bisync',
      py_modules = ['bisync_lib'],
      packages=[],
      scripts=["bisync"],
      long_description="A distributed bidirectional folder synchronizer.",
      keywords="",
      license="GPLv3",
      classifiers=[
          ],
     )

