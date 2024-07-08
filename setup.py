import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="python-smarttub",
    version="0.0.37",
    author="Matt Zimmerman",
    author_email="mdz@alcor.net",
    description="API to query and control hot tubs using the SmartTub system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mdz/python-smarttub",
    packages=["smarttub"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "aiohttp>=3.7.4,<4",
        "inflection~=0.5",
        "pyjwt~=2.4",
        "python-dateutil~=2.8",
    ],
    # Note: tests require python >=3.8
    tests_require=[
        "pytest",
        "pytest-asyncio",
        "aresponses",
    ],
    python_requires=">=3.7",
)
