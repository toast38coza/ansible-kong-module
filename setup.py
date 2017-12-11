from setuptools import setup

long_description=open('README.rst', 'r').read()
version=open('VERSION', 'r').read()

setup(
    name='ansible-kong',
    version=version,
    description='Kong 0.11.x module and Python library for Ansible',
    long_description=long_description,
    author='Timo Beckers',
    author_email='timo.beckers@klarrio.com',
    url='https://github.com/Klarrio/ansible-kong-module',
    packages=['library', 'module_utils'],
    package_dir={'ansible': ''},
    install_requires = [
        'ansible>=2.1.0',
        'ansible-dotdiff'
    ],
)
