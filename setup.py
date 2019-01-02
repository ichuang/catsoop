import glob
from setuptools import setup

from catsoop import __version__

requirements = open("requirements.txt").read().split('\n')

setup(
    name='catsoop',
    version=__version__,
    author='CAT-SOOP Contributors',
    author_email='catsoop-dev@mit.edu',
    packages=['catsoop', 'catsoop.test', 'catsoop.thirdparty', 'catsoop.scripts'],
    scripts=[],
    url='https://catsoop.mit.edu',
    license='AGPLv3+',
    description='CAT-SOOP is a tool for automatic collection and assessment of online exercises.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'catsoop = catsoop.main:command_line_interface',
            ],
        },
    install_requires=requirements,
    package_dir={'catsoop': 'catsoop'},
    package_data={'catsoop': ['scripts/*']},
    test_suite="catsoop.test",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Education",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
    ]
)
