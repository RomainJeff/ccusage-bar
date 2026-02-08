from setuptools import setup

setup(
    app=["app.py"],
    data_files=["icon-44.png"],
    options={
        "py2app": {
            "argv_emulation": False,
            "iconfile": "app-icon.icns",
            "plist": {
                "LSUIElement": True,
                "CFBundleName": "ccusage-bar",
                "CFBundleIdentifier": "com.romainjeff.ccusage-bar",
                "CFBundleVersion": "1.0.0",
            },
            "packages": ["rumps"],
            "includes": ["ccusage_client", "config", "user_config", "preferences", "menu_formatter", "login_item_manager", "update_manager"],
            "excludes": [
                "numpy",
                "numba",
                "PIL",
                "setuptools",
                "pkg_resources",
                "wheel",
                "pip",
                "test",
                "distutils",
                "unittest",
                "tkinter",
                "matplotlib",
                "pandas",
                "scipy",
            ],
        }
    },
    setup_requires=["py2app"],
)
