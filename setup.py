"""Setup script for Call Intelligence System."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README_PRODUCTION.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="call-intelligence-system",
    version="1.0.0",
    description="Enterprise-grade browser automation and call analysis with advanced ML/AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourorg/call-intelligence",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
            "pytest-playwright>=0.4.4",
            "black>=23.12.0",
            "flake8>=7.0.0",
            "mypy>=1.8.0"
        ],
        "gpu": [
            "llama-cpp-python[cuda]"
        ]
    },
    entry_points={
        "console_scripts": [
            "call-intelligence=recorder.app_ml_integrated:main",
            "call-intelligence-api=recorder.api.main:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    keywords="browser automation, ml, ai, llm, rag, transcription, call-intelligence",
)
