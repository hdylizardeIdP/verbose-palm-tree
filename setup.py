from setuptools import setup, find_packages

setup(
    name="schwab-investment-app",
    version="0.2.0",
    description="Investment app with web dashboard using Charles Schwab API for automated trading strategies",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.31.0",
        "schwab-py>=1.4.0",
        "python-dotenv>=1.0.0",
        "click>=8.1.0",
        "rich>=13.7.0",
        "pandas>=2.1.0",
        "numpy>=1.24.0",
        "flask>=3.0.0",
        "schedule>=1.2.0",
        "python-json-logger>=2.0.7",
    ],
    package_data={
        "schwab_app": [
            "templates/*.html",
            "static/css/*.css",
            "static/js/*.js",
        ],
    },
    entry_points={
        "console_scripts": [
            "schwab-invest=schwab_app.cli:main",
        ],
    },
    python_requires=">=3.8",
)
