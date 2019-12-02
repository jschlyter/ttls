#!/usr/bin/env python

from setuptools import setup
from ttls import __version__


setup(
    name='ttls',
    version=__version__,
    description='Twinkly Twinkly Little Star',
    long_description="""\
ttls (Twinkly Twinkly Little Star) can help you make async requests to
Twinkly LEDs. A commmand line utility is also included.
""",
    author='Jakob Schlyter',
    author_email='jakob@schlyter.se',
    license='BSD',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    url='https://github.com/jschlyter/ttls',
    packages=['ttls'],
    install_requires=[
        'aiohttp',
        'colour',
        'setuptools',
    ],
    entry_points={
        "console_scripts": [
            "ttls = ttls.cli:main",
        ]
    }
)
