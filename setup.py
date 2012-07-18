#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
  name="bots",
  version="0.1",
  packages=find_packages(),

  install_requires=['pyjabberbot', 'pyrrd'],

  include_package_data = True,

  entry_points={
    'console_scripts': [
      'kilram = kilram.kilram:main',
      'grumnus = grumnus.grumnus:main'
    ]
  },

  author="Rodolfo Granata",
  author_email="warlock.cc@gmail.com",
  description="A test bot for my server",
)

# vim: set sw=2 sts=2 : #
