"""
Setup script for Enhanced NLvoorelkaar Outreach Tool
"""

from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="nlvoorelkaar-enhanced",
    version="2.0.0",
    author="Enhanced Development Team",
    author_email="support@nlvoorelkaar-tool.com",
    description="Enhanced NLvoorelkaar volunteer outreach tool with modern UI and advanced features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nlvoorelkaar-enhanced/tool",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Email",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
    },
    entry_points={
        "console_scripts": [
            "nlvoorelkaar-enhanced=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    data_files=[
        ("", ["README.md", "requirements.txt"]),
    ],
    zip_safe=False,
    keywords="nlvoorelkaar volunteer outreach automation scraping",
    project_urls={
        "Bug Reports": "https://github.com/nlvoorelkaar-enhanced/tool/issues",
        "Source": "https://github.com/nlvoorelkaar-enhanced/tool",
        "Documentation": "https://github.com/nlvoorelkaar-enhanced/tool/wiki",
    },
)

