from setuptools import setup


package_name = "arm_control"


setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/arm_control.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="OpenCode",
    maintainer_email="dev@example.com",
    description="Future robot-arm execution package for the smart shadow lamp system.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "arm_controller = arm_control.arm_controller_node:main",
        ],
    },
)
