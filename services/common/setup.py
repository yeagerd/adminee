from setuptools import setup  # type: ignore[import-unresolved]

setup(
    name="common",
    version="0.1.0",
    packages=["common"],
    package_dir={"common": "."},
    python_requires=">=3.8",
    install_requires=[
        "structlog>=23.1.0",
        "fastapi>=0.68.0",
    ],
    description="Common utilities and shared code for Briefly services",
)
