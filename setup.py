from setuptools import setup, find_packages

setup(
    name="hw3",
    version="0.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "fastapi",
        "uvicorn",
        "asyncpg",
        "redis",
        # другие зависимости из requirements.txt
    ],
)
