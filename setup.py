from os import path
from setuptools import setup, find_packages


#this should hopefully allow us to have a more pypi friendly, always up to date readme
readMeDir = path.abspath(path.dirname(__file__))
with open(path.join(readMeDir, 'README.md'), encoding='utf-8') as readFile:
    long_desc = readFile.read()


VERSION = '1.4.8'

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
    long_description=long_desc,
    long_description_content_type='text/markdown',
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
