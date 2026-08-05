from setuptools import setup

setup(
    name="fjsti-id",
    version="1.0.0",
    packages=["fjsti_id"],
    package_dir={"fjsti_id": "fjsti_id"},
    install_requires=["httpx>=0.27"],
    description="FJSTI ID client SDK",
)
