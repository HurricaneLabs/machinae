import subprocess
from setuptools import setup, find_packages


cmd = 'pandoc -f markdown_github -t rst README.md --no-wrap'
long_description = subprocess.check_output(cmd, shell=True, universal_newlines=True)

VERSION = '1.0.0'

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
    long_description=long_description,
    install_requires=[
        'dnspython3',
        'ipwhois',
        'requests',
        'stopit',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'machinae = machinae.cmd:main',
        ]
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Development Status :: 4 - Beta',
    ],
    bugtrack_url='https://github.com/HurricaneLabs/machinae/issues',
)
