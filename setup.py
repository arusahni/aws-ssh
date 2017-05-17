"""Set up the package."""

import re
import sys
from setuptools import setup, find_packages

try:
    import pypandoc
    LONG_DESCRIPTION = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    LONG_DESCRIPTION = open('README.md').read()

REQUIREMENTS = [
    'boto3',
    'pexpect',
    'six',
    'tqdm',
]

if sys.version_info <= (3,):
    REQUIREMENTS.append('configparser>=3.5.0') # Using the beta for PyPy compatibility

with open('aws_ssh/__init__.py', "r") as f:
    VERSION = re.search(r"^__version__\s*=\s*[\"']([^\"']*)[\"']", f.read(), re.MULTILINE).group(1)

setup(name='aws-ssh',
      version=VERSION,
      description='A utility to enable easy SSH connections to AWS EC2 instances.',
      long_description=LONG_DESCRIPTION,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
          'Topic :: System :: Systems Administration',
      ],
      keywords='aws ssh ec2 iam amazon web services remote',
      author='Aru Sahni',
      author_email='arusahni@gmail.com',
      url='https://github.com/arusahni/aws-ssh',
      license='MIT',
      package_data={'': ['LICENSE']},
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=REQUIREMENTS,
      entry_points={
          'console_scripts': ['aws-ssh-cli=aws_ssh.cli:print_ssh_args'],
      },
      scripts=['bin/awssh', 'bin/aws-ssh', 'bin/ssh-ec2'],
      extras_require={
          'dev': ['mock', 'pytest', 'coverage', 'pylint', 'pytest-cov', 'pypandoc'],
      },
     )
