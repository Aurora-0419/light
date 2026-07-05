from setuptools import setup


package_name = "light_control"


setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/light_control.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="OpenCode",
    maintainer_email="dev@example.com",
    description="Future light execution package for the smart shadow lamp system.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "light_controller = light_control.light_controller_node:main",
        ],
    },
)
