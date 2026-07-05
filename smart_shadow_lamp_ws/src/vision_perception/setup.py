from setuptools import setup


package_name = "vision_perception"


setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/vision_perception.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="OpenCode",
    maintainer_email="dev@example.com",
    description="ROS2 wrapper package for smart shadow lamp visual perception.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "vision_state_bridge = vision_perception.vision_state_bridge:main",
        ],
    },
)
