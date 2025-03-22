from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='giorgio',
    version='0.2.3',
    description='A lightweight micro-framework for script automation with a GUI.',
    long_description=long_description,
    long_description_content_type="text/markdown",
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
    python_requires='>=3.6',
    keywords='automation, cli, gui, scripts, micro-framework',
    project_urls={
       'Documentation': 'https://github.com/officinaMusci/giorgio#readme',
       'Bug Tracker': 'https://github.com/officinaMusci/giorgio/issues',
    },
)
