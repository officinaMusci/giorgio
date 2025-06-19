import re
from pathlib import Path
import setuptools

# The directory containing this file
HERE = Path(__file__).parent

# Read the long description from README.md if it exists (optional)
README = (HERE / "README.md").read_text(encoding="utf-8") if (HERE / "README.md").exists() else ""

# Extract the version from the __init__.py file
pkg_dir = Path(__file__).parent / "giorgio"
init_py = (pkg_dir / "__init__.py").read_text()
VERSION = re.search(r'__version__ = ["\']([^"\']+)["\']', init_py).group(1)

setuptools.setup(
    name="giorgio",
    version=VERSION,
    description="Giorgio: a micro-framework for interactive Python scripts",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Danilo Musci",
    author_email="officina@musci.ch",
    url='https://github.com/officinaMusci/giorgio',
    packages=setuptools.find_packages(exclude=("tests",)),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "typer>=0.9.0",
        "questionary>=1.10.0",
        "python-dotenv>=1.0.0"
    ],
    entry_points={
        "console_scripts": [
            "giorgio=giorgio.cli:app",
        ]
    },
    keywords='automation, cli, gui, scripts, micro-framework',
    project_urls={
       'Documentation': 'https://github.com/officinaMusci/giorgio#readme',
       'Bug Tracker': 'https://github.com/officinaMusci/giorgio/issues'
    },
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License"
    ]
)
