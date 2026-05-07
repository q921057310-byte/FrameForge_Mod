import os

from setuptools import setup

version_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "freecad", "frameforge2", "version.py")
with open(version_path) as fp:
    exec(fp.read())

setup(
    name="frameforge2",
    version=str(__version__),
    packages=["freecad", "freecad.frameforge2"],
    maintainer="Your Name",
    maintainer_email="your-email@example.com",
    url="https://github.com/your-username/FrameForge2",
    description="FrameForge2 - Fork of FrameForge for creating Frames and Beams.",
    include_package_data=True,
)
