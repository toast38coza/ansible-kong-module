from setuptools import setup

files = [
    "ansible/modules/kong",
    "ansible/module_utils/kong",
]

long_description = open('README.md', 'r').read()
version = open('VERSION', 'r').read()

setup(
    name='ansible-modules-kong',
    version=version,
    description='Ansible Modules for Kong 0.14.x.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Timo Beckers',
    author_email='timo.beckers@klarrio.com',
    url='https://github.com/Klarrio/ansible-kong-module',
    packages=files,
    install_requires=['ansible>=2.4.0', 'ansible-dotdiff'],
)
