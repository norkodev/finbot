from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="finbot",
    version="0.1.0",
    author="Finbot Developer",
    author_email="dev@finbot.com",
    description="Sistema de Inteligencia Financiera Personal",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/norkodev/finbot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "pdfplumber>=0.10.0",
        "sqlalchemy>=2.0.0",
        "pandas>=2.1.0",
        "python-dateutil>=2.8.0",
        "unidecode>=1.3.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fin=fin.cli:cli",
        ],
    },
)
