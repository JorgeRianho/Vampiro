[app]
title = Vampiro
package.name = vampiro
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,txt
source.exclude_dirs = .buildozer,.venv_morph39,.venv_morph310,bin,__pycache__
version = 0.1
requirements = python3,kivy,cython==0.29.36
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.9.1
fullscreen = 0
android.build_tools_version = 33.0.2
android.api = 33
android.minapi = 26
android.ndk = 25b
android.ndk_api = 26
android.skip_update = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
