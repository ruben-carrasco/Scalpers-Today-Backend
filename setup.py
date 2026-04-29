from setuptools import find_packages, setup

setup(
    name="scalper_today",
    version="15.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
