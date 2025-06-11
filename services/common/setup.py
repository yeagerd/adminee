from setuptools import setup

setup(
    name="common",
    version="0.1.0",
    packages=["common"],
    package_dir={"common": "."},
    python_requires=">=3.8",
    description="Common utilities and shared code for Briefly services",
)
