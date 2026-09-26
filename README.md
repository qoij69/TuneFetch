## Build

Linux / macOS:
```
source build/envsetup.sh
lunch                       # pick a target, or: lunch tunefetch-linux-userdebug
make tunefetch               # or: m / mka / mm
```

Windows (cmd.exe):
```
call build\envsetup.bat
call build\lunch.bat
make tunefetch
```

`lunch tunefetch-allproducts-eng` instead sets up the GitHub Actions
workflow (`build/ci/build.yml`) so all three targets build in the
cloud on every push - useful since PyInstaller can't cross-compile
(a target only builds natively on its own OS).

`make clean` removes `out/` and the build sandbox.
