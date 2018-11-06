#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import find_packages, setup


description = "Adapt boto3 to pyramid"
here = os.path.abspath(os.path.dirname(__file__))
try:
    readme = open(os.path.join(here, "README.rst")).read()
    changes = open(os.path.join(here, "CHANGES.txt")).read()
    long_description = "\n\n".join([readme, changes])
except OSError:
    long_description = description


install_requires = ["boto3", "botocore", "pyramid"]


setup(
    name="pyramid_boto3",
    version="0.3.dev1",
    description=description,
    long_description=long_description,
    author="OCHIAI, Gouji",
    author_email="gjo.ext@gmail.com",
    url="https://github.com/gjo/pyramid_boto3",
    license="BSD",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        ':python_version<"3.4"': ["pyramid_services<2.0"],
        ':python_version>="3.4"': ["pyramid_services"],
    },
    classifiers=[
        "Framework :: Pyramid",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
