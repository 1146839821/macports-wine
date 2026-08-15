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
itself to build from source. MacPorts distfiles and a 3 GB compiler cache are
restored between runs; the MacPorts prefix itself is deliberately not cached.

Successful runs upload `wine.tar.xz`, a relocatable `wine/bin`, `wine/lib`, and
`wine/share` tree. It contains Wine's private files, Wine Mono and Gecko,
GStreamer/FFmpeg, MoltenVK, SDL2, and the other top-level runtime libraries.
Mach-O install names and search paths are rewritten to relative `@rpath` and
`@loader_path` references before the archive is audited and signed. Failed runs
still upload the MacPorts build log and available configure logs.

For Rosetta stack-overflow diagnosis the workflow builds three artifacts:

- `full`: the normal build with all Endfield FineWine patches;
- `control`: the same build without the newly imported Endfield patch sets;
- `rosetta-stack`: the full build with a diagnostic 32 MiB minimum thread-stack
  reserve under Rosetta. The Windows guard page remains enabled.

Run the same game and Wine prefix with all three archives. A passing `control`
points to an Endfield patch regression; a passing `rosetta-stack` with failing
`full` indicates finite stack pressure; if all three fail similarly, the most
likely cause is an unbounded exception/call recursion or Rosetta itself.

Extract and verify the archive with:

```sh
tar -xJf wine.tar.xz
./wine/bin/wine --version
```

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
