from setuptools import setup, find_packages

setup(
    name='giorgio',
    version='0.1.0',
    description='A lightweight micro-framework for script automation with a GUI.',
    author='Danilo Musci',
    author_email='officina@musci.ch',
    url='https://github.com/officinaMusci/giorgio',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'giorgio=giorgio.cli:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
