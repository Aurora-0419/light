from setuptools import setup


package_name = "system_coordinator"


setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", [
            "launch/system_coordinator.launch.py",
            "launch/shadow_lamp_sim.launch.py",
        ]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="OpenCode",
    maintainer_email="dev@example.com",
    description="Thin orchestration package for the smart shadow lamp system.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "system_coordinator = system_coordinator.coordinator_node:main",
        ],
    },
)
