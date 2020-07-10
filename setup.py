import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="python-smarttub",
    version="0.0.2",
    author="Matt Zimmerman",
    author_email="mdz@alcor.net",
    description="API to query and control hot tubs using the SmartTub system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mdz/python-smarttub",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'requests',
        'pyjwt',
        'python-dateutil',
    ],
    tests_require=['requests-mock'],
    python_requires='>=3.6',
)
