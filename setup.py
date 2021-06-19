# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, 'requirements.txt')) as f:
    requirements = f.split("\n")


setup(
    name='loult-server',
    version='0.1.0',
    description='The Loult Server',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/loult-elte-fwre/loult-ng/',
    author='LoultCorp',
    author_email='loult@loult.family',
    license="MIT",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8'
    ],
    keywords='',
    namespace_packages=['loult_serv'],
    packages=find_packages(),
    install_requires=requirements,
    setup_requires=['pytest-runner', 'setuptools>=38.6.0'],  # >38.6.0 needed for markdown README.md
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'loult-serv = loult_serv:main',
        ]
    }
)
