from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

with open("README.md") as f:
    long_description = f.read()

setup(
    name="insurance_agent_mgmt",
    version="1.0.0",
    description="Insurance Agent Management for ERPNext V15+",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Organization",
    author_email="admin@yourorg.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
