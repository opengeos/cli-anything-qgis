from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-qgis",
    version="1.0.0",
    description="Command-line interface for QGIS — operate QGIS GIS without a GUI",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    package_data={
        "cli_anything.qgis": ["skills/*.md"],
    },
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-qgis=cli_anything.qgis.qgis_cli:main",
        ],
    },
    python_requires=">=3.10",
)
