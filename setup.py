
from setuptools import setup, find_packages

url = "https://github.com/AaronWatters/volume_gizmos"
version = "0.1.0"
readme = open('README.md').read()

setup(
    name="volume_gizmos",
    packages=find_packages(),
    version=version,
    description="Browser based interactive 3d data array visualizations",
    long_description=readme,
    long_description_content_type="text/markdown",
    #include_package_data=True,
    author="Aaron Watters",
    author_email="awatters@flatironinstitute.org",
    url=url,
    install_requires=[
        "jp_doodle",
        "numpy",
        "H5Gizmos",
        ],
    scripts = [
        # none yet.
    ],
    python_requires=">=3.6",
    # Javascript modules are frozen into the distribution.
    include_package_data=True,
    package_data={
        'volume_gizmos': [
            'node_modules/**/*',  # Include all files its subdirectories
            'package.json',
        ],
    },
)
