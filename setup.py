from setuptools import setup, find_packages

setup(
    name='Machinae',
    version='1.0',
    author='Steve McMaster',
    author_email='mcmaster@hurricanelabs.com',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    zip_safe=False,
    url='https://github.com/HurricaneLabs/machinae',
    description='Machinae Security Intelligence Collector',
    install_requires=[
        "dnspython3",
        "ipwhois",
        "requests",
        "pyyaml",
    ],
    entry_points={
        'console_scripts': [
            'machinae = machinae.cmd:main',
        ]
    },
)
