import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

name = "awsenum"

setuptools.setup(
    name=name,
    version="0.0.1",
    author="Eloy Perez Gonzalez",
    author_email="zer1t0ps@protonmail.com",
    description="Enumerate AWS permissions and resources",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "awsenum = awsenum.main:main",
        ]
    },
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
)
