# macports-wine
A MacPorts overlay that provides recent versions of wine.

<br>

## This repository provides
- `CrossOver`               *(v26.1.0)*
- `crossovertricks`         *(winetricks wrapper for CrossOver)*
- `game-porting-toolkit`    *(v1.1)*
- `gstreamer.framework`     *(v1.28.1)*
- `gstreamer-runtime`       *(v1.28.1)*
- `gstreamer-development`   *(v1.28.1)*
- `libinotify`              *(v20240724)*
- `MacOSX.sdk`              *(Multiple MacOSX SDKs)*
- `mingw-w64-pkgconfig`
- `wine-stable`             *(v11.0)*
- `wine-devel`              *(v11.8)*
- `wine-staging`            *(v11.8)*
- `winetricks`              *(v20251121)*
- `sikarugir`               *(v1.0.1)*

<br>

## How to use this repository
After installing MacPorts you need a modern version of `git`\
git clone the repository into /opt then follow [4.7. Local Portfile Repositories](https://guide.macports.org/#development.local-repositories)\
Next run `port -v sync` you can now install any of the provided Ports.

## CI build
The [Build Wine 11.8](.github/workflows/wine-devel-11.8.yml) GitHub Actions
workflow builds `emulators/wine-devel` on an Intel macOS 15 runner. It can be
started manually and also runs when the Wine Portfile, its local dependencies,
patches, or the workflow itself change.

The job installs a checksum-pinned MacPorts release, registers this repository
before the official ports tree, installs dependencies, and forces `wine-devel`
itself to build from source. Successful runs upload both the single-port
MacPorts image and a `runtime-prefix` archive containing Wine plus its recursive
library and runtime dependencies, including GStreamer/FFmpeg, MoltenVK, SDL2,
Wine Mono, and Wine Gecko. Failed runs still upload the MacPorts build log and
available configure logs.

The runtime archive keeps MacPorts' `/opt/local` layout because Wine's Mach-O
load commands and framework paths use that prefix. Extract it on a clean target
machine with:

```sh
sudo tar -xzf wine-devel-11.8-runtime-prefix-macos-15-intel.tar.gz -C /
/opt/local/bin/wine --version
```

Do not extract it over an unrelated existing MacPorts installation unless you
intend to replace files in that prefix.

<br>

### macOS Mojave
Add the following into `/opt/local/etc/macports/macports.conf`
```
macosx_deployment_target     10.13
macosx_sdk_version           10.13
```
This enables the `i386` & `x86_64` architectures thus enabling the `+universal` flag\
Next place a copy of the `MacOSX10.13.sdk` into `/Library/Developer/CommandLineTools/SDKs/`

<br>

### Apple Silicon systems, force x86_64
Due to macports-ports bugs we need to force MacPorts to only install for x86_64
> echo "build_arch x86_64" | sudo tee -a /opt/local/etc/macports/macports.conf >/dev/null
