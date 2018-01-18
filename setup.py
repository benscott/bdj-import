
from pip.req import parse_requirements
from setuptools import setup

install_requirements = parse_requirements('./requirements.txt', session=False)
requirements = [str(ir.req) for ir in install_requirements]

setup(
    name='bdj_import',
    version='0.1',
    description='Import data into ARPHA Writing Tool (AWT) Biodiversity Data Journal',
    author='Ben Scott',
    author_email='ben@benscott.co.uk',
    packages=['bdj_import'],
    install_requires=requirements,
    entry_points={}
)
