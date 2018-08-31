import subprocess
from setuptools import setup, find_packages


def get_long_description():
    cmd = 'pandoc -f markdown_github -t rst README.md --no-wrap'
    try:
        return subprocess.check_output(cmd, shell=True, universal_newlines=True)
    except:
        return ""

VERSION = '1.4.1'

setup(
    name='machinae',
    version=VERSION,
    author='Steve McMaster',
    author_email='mcmaster@hurricanelabs.com',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    zip_safe=False,
    url='http://hurricanelabs.github.io/machinae/',
    description='Machinae Security Intelligence Collector',
    long_description=get_long_description(),
    install_requires=[
        'dnspython3',
        'ipwhois<0.11',
        'requests',
        'stopit',
        'pyyaml',
        'beautifulsoup4',
        'html5lib',
        'relatime',
        'tzlocal',
        'filemagic',
        'feedparser',
        'defang',
    ],
    entry_points={
        'console_scripts': [
            'machinae = machinae.cmd:main',
        ]
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Development Status :: 5 - Production/Stable',
    ],
    bugtrack_url='https://github.com/HurricaneLabs/machinae/issues',
)
