"""
Setup script for JITX EMN/IDF Importer
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="jitx-emn-importer",
    version="1.0.0",
    author="JITX Inc.",
    description="EMN/IDF importer for JITX Python - converts mechanical CAD data to JITX geometry",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        # JITX Python dependencies will be specified when available
        # "jitx>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "emn-import=jitx_emn_importer.emn_importer:main",
        ],
    },
    keywords="jitx pcb eda emn idf bdf mechanical import",
    project_urls={
        "Bug Reports": "https://github.com/JITx-Inc/jitx-emn-importer/issues",
        "Source": "https://github.com/JITx-Inc/jitx-emn-importer",
        "Documentation": "https://docs.jitx.com/",
    },
)