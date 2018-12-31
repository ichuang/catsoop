import glob
from setuptools import setup

requirements = open("requirements.txt").read().split('\n')

setup(
    name='catsoop',
    version='0.9',
    author='catsoop-users@mit.edu',
    author_email='catsoop-users@mit.edu',
    packages=['catsoop', 'catsoop.test'],
    scripts=[],
    url='http://pypi.python.org/pypi/catsoop/',
    license='LICENSE.txt',
    description='CAT-SOOP is an Automatic Tutor for Six-Oh-One Problems',
    long_description=open('README.md').read(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'catsoop = catsoop.main:CommandLine',
            ],
        },
    install_requires=requirements,
    package_dir={'catsoop': 'catsoop'},
    package_data={'catsoop': ['scripts/*']},
    # data_files = data_files,
    test_suite="catsoop.test",
)
