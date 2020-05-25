import re
from setuptools import setup, find_packages
import platform

# Plaform Constants
LINUX, MAC, WINDOWS = "Linux", "Darwin", "Windows"

SHORT_DESCRIPTION = "Figgy is a security focused cloud-native configuration and secret management platform with a goal of " \
              "providing a simple workflow for securely and resiliently managing, version, and sharing application " \
              "configurations and secrets."

LONG_DESCRIPTION = "Figgy is a security focused cloud-native configuration and secret management platform with a goal of " \
              "providing a simple workflow for securely and resiliently managing, version, and sharing application " \
              "configurations and secrets."

with open('config/figgy.py') as file:
    contents = file.read()
    VERSION = re.search('^VERSION\s*=\s*"(.*)"', contents, re.MULTILINE)
    GITHUB = re.search('^FIGGY_GITHUB\s*=\s*"(.*)"', contents, re.MULTILINE)


with open('./requirements.txt', 'r') as file:
    requirements = file.readlines()

if platform.system() == WINDOWS:
    with open('./requirements-windows.txt', 'r') as file:
        requirements += file.readlines()

if platform.system() == LINUX:
    with open('./requirements-linux.txt', 'r') as file:
        requirements += file.readlines()

setup(
    name="figgy",
    packages=find_packages() + ['.'],
    entry_points={
        "console_scripts": ['figgy = figgy:main']
    },
    version=VERSION,
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author="Jordan Mance",
    author_email="jordan@figgy.dev",
    url=GITHUB,
    python_requires='>=3.6',
    install_requires=requirements
)