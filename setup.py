import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="clustertools",
    version="0.1.dev1",
    author="Jeremy J. Webb",
    author_email="webb@astro.utoronto.ca",
    description="A python packaged for analysing star clusters",
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    packages=["clustertools","clustertools/analysis","clustertools/util"],
    install_requires=['numpy>=1.7','scipy','galpy','numba','limepy','seaborn']
    )
