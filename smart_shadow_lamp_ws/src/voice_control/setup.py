from setuptools import setup


package_name = "voice_control"


setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/voice_control.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="OpenCode",
    maintainer_email="dev@example.com",
    description="ROS2 wrapper package for smart shadow lamp voice control.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "voice_command_bridge = voice_control.voice_command_bridge:main",
            "voice_feedback_bridge = voice_control.voice_feedback_bridge:main",
        ],
    },
)
