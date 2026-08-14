#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 3 ]]; then
  echo "usage: $0 <package-root> <archive> <expected-version>" >&2
  exit 2
fi

package_root="$1"
archive="$2"
expected_version="$3"
script_dir="$(cd "$(dirname "$0")" && pwd)"

test -x "${package_root}/bin/wine"
test -x "${package_root}/bin/wineserver"
test -d "${package_root}/lib/wine/x86_64-unix"
test -d "${package_root}/lib/wine/i386-windows"
test -d "${package_root}/lib/wine/x86_64-windows"
test -d "${package_root}/lib/GStreamer.framework"
test -f "${package_root}/lib/libMoltenVK.dylib"
find "${package_root}/lib" -maxdepth 1 -name 'libSDL2*.dylib' -print -quit \
  | grep -q .
find "${package_root}/lib/GStreamer.framework" -name 'libavcodec*.dylib' \
  -print -quit | grep -q .
test -d "${package_root}/share/wine/mono/wine-mono-11.1.0"
find "${package_root}/share/wine/gecko" -maxdepth 1 \
  -name 'wine-gecko-2.47.4-*' -print -quit | grep -q .

top_level="$({
  find "${package_root}" -mindepth 1 -maxdepth 1 -type d -exec basename {} \;
} | sort | tr '\n' ' ')"
test "${top_level}" = "bin lib share "

/usr/bin/python3 "${script_dir}/relocate-wine-macho.py" --audit \
  "${package_root}" /opt/local

wine_version="$("${package_root}/bin/wine" --version)"
printf 'Packaged Wine version: %s\n' "${wine_version}"
[[ "${wine_version}" == "wine-${expected_version}"* ]]

test -f "${archive}"
archive_listing="$(mktemp)"
trap 'rm -f "${archive_listing}"' EXIT
/usr/bin/tar -tJf "${archive}" > "${archive_listing}"
grep -Eq '^wine/bin/wine$' "${archive_listing}"
grep -Eq '^wine/lib/wine/' "${archive_listing}"
grep -Eq '^wine/share/wine/' "${archive_listing}"
if grep -Eq '(^|/)opt/local/' "${archive_listing}"; then
  echo "archive unexpectedly contains an opt/local prefix" >&2
  exit 1
fi

printf 'Portable package audit passed: %s\n' "${archive}"
