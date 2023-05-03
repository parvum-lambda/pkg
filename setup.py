from setuptools import setup, find_packages
import os

if __name__ == '__main__':
    setup(
        version=os.getenv('NEW_VERSION'),
        packages=find_packages(),
        package_data={
            'app': ['pkg/*'],
        }
    )
