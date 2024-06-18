from setuptools import setup, find_packages

setup(
    name='policyengine',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'policyengine_us',
        'policyengine_uk',
        #'policyengine_canada'
    ],
     extras_require={
        "dev": [
            "black",
            "jupyter-book",
            "pytest"
        ]
     }
)