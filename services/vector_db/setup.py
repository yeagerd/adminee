from setuptools import setup  # type: ignore[import-unresolved]

setup(
    name="vector_db",
    version="0.1.0",
    packages=["vector_db"],
    package_dir={"vector_db": "."},
    python_requires=">=3.8",
    description="Vector database utilities for Briefly services",
)
