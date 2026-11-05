from pathlib import Path
from setuptools import setup, find_packages

README = Path(__file__).parent / "README.md"

setup(
    name="englishai",
    version="0.5.7",
    description="Rule-based symbolic English parsing and reasoning engine",
    long_description=README.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "englishai.version2": ["rules.txt"],
    },
    python_requires=">=3.8",
    install_requires=[],
    include_package_data=True,
)
