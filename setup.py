"""Setup script for Auton8 Recorder (backward compat with pyproject.toml)."""

from setuptools import setup, find_packages
from pathlib import Path

readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Minimal requirements only - tester machines
minimal_requirements = [
    "PySide6>=6.6.0",
    "websockets>=12.0",
    "pydantic>=2.10.0",
    "playwright>=1.47.0",
    "numpy>=1.26.3",
]

setup(
    name="auton8-recorder",
    version="1.0.0",
    description="Browser automation recorder with ML-powered self-healing replay",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=minimal_requirements,
    extras_require={
        "ml-core": [
            "scikit-learn>=1.4.0",
            "xgboost>=2.0.3",
            "opencv-python>=4.9.0",
            "nltk>=3.8.1",
            "rapidfuzz>=3.6.1",
            "imagehash>=4.3.1",
        ],
        "ml-advanced": [
            "torch>=2.1.0",
            "transformers>=4.36.2",
            "sentence-transformers>=2.3.1",
            "faiss-cpu>=1.7.4",
            "spacy>=3.7.2",
        ],
        "server": [
            "fastapi>=0.109.0",
            "uvicorn>=0.25.0",
            "sqlalchemy>=2.0.25",
        ],
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "auton8-recorder=recorder.app_enhanced:main",
            "auton8-server=recorder.api.main:start",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.10",
)
