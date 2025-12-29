from setuptools import find_packages, setup

setup(
    name="vagrantp",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
