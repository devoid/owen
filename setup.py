import os.path
from setuptools import setup, find_packages

cwd = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(cwd, 'requirements.txt')) as f:
    required = f.read().splitlines()


setup(
    name='owen',
    description='owen: create service ticekts with vendors',
    version='0.1.0',
    author='Scott Devoid',
    author_email='devoid@anl.gov',
    url='https://github.com/devoid/owen',
    license='LICENSE.txt',
    long_description=open(cwd + '/README.txt').read(),
    packages=find_packages(),
    install_requires=required,
    entry_points={
        'console_scripts' : [
              'ibm-service = owen.cmd.ibm_service',
              'ibm-ticket = owen.cmd.ibm_ticket',
        ],
    },
)

