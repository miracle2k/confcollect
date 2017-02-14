#!/usr/bin/env python
# coding: utf-8
from setuptools import setup, find_packages

setup(
    name="confcollect",
    description="Helpers to collect configuration from os environment, files etc.",
    author='Michael Elsdoerfer',
    author_email='michael@elsdoerfer.com',
    url='https://github.com/miracle2k/confcollect',
    version="0.2.4",
    license='BSD',
    py_modules=['confcollect'],
    zip_safe=True,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'License :: OSI Approved :: BSD License',
    ]
)
