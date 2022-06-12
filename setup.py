import setuptools

# Update current version here
current_version = "0.0.1"

# Save this version for later use in a text file accessible from app
with open("src/warden/static/version.txt", "w") as text_file:
    print(f"{current_version}", file=text_file)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="warden-monitor-alphazeta",
    version=current_version,
    author="AlphaZeta",
    author_email="alphaazeta@protonmail.com",
    description="Monitor bitcoin addresses in realtime",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pxsocs/warden_monitor",
    project_urls={
        "Bug Tracker": "https://github.com/pxsocs/warden_monitor/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
