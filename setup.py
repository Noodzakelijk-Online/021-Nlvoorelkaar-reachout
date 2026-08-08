"""Package metadata for NLvoorelkaar Reachout."""

from pathlib import Path

from setuptools import find_packages, setup

from config.version import __version__


ROOT = Path(__file__).parent
requirements = [
    line.strip()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
]

setup(
    name="nlvoorelkaar-reachout",
    version=__version__,
    author="Noodzakelijk Online",
    description="Local-first, review-gated NLvoorelkaar outreach operations",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/Noodzakelijk-Online/021-Nlvoorelkaar-reachout",
    packages=find_packages(),
    py_modules=["main", "nlve_cli", "run"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.10,<3.13",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "nlve=nlve_cli:main",
            "nlve-gui=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="volunteer outreach review approval privacy local-first",
    project_urls={
        "Issues": "https://github.com/Noodzakelijk-Online/021-Nlvoorelkaar-reachout/issues",
        "Source": "https://github.com/Noodzakelijk-Online/021-Nlvoorelkaar-reachout",
    },
)
