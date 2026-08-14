#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 3 ]]; then
  echo "usage: $0 <macports-prefix> <package-parent> <metadata-dir>" >&2
  exit 2
fi

prefix="$(cd "$1" && pwd)"
package_parent="$2"
metadata_dir="$3"
package_root="${package_parent}/wine"
port_command="${prefix}/bin/port"
script_dir="$(cd "$(dirname "$0")" && pwd)"

if [[ -e "${package_root}" ]]; then
  echo "package destination already exists: ${package_root}" >&2
  exit 1
fi

mkdir -p \
  "${package_root}/bin" \
  "${package_root}/lib" \
  "${package_root}/share" \
  "${metadata_dir}"

runtime_ports="${metadata_dir}/package-runtime-ports.txt"
runtime_libraries="${metadata_dir}/package-runtime-libraries.txt"

{
  printf '%s\n' wine-devel
  "${port_command}" -q rdeps --no-build --no-test wine-devel +gstreamer
} \
  | /usr/bin/sed -E \
      -e 's/^[[:space:]]+//' \
      -e 's/[[:space:]].*$//' \
  | /usr/bin/awk 'NF && !seen[$0]++' \
  > "${runtime_ports}"

for required_runtime_port in \
  gstreamer.framework \
  MoltenVK-latest \
  libsdl2 \
  mingw-w64-wine-gecko-2.47.4 \
  mingw-w64-wine-mono-11.1.0; do
  grep -Fxq "${required_runtime_port}" "${runtime_ports}"
done

# Wine's executables share ${prefix}/bin with every installed port, so only
# copy files owned by wine-devel. Wine's private lib and share directories are
# safe to copy as directories; share/wine also contains the Mono and Gecko
# runtime ports.
while IFS= read -r source_path; do
  source_path="${source_path#${source_path%%[![:space:]]*}}"
  case "${source_path}" in
    "${prefix}/bin/"*)
      relative_path="${source_path#"${prefix}/bin/"}"
      destination="${package_root}/bin/${relative_path}"
      mkdir -p "$(dirname "${destination}")"
      /bin/cp -pP "${source_path}" "${destination}"
      ;;
  esac
done < <("${port_command}" -q contents wine-devel)

/usr/bin/ditto "${prefix}/lib/wine" "${package_root}/lib/wine"
/usr/bin/ditto "${prefix}/share/wine" "${package_root}/share/wine"
/usr/bin/ditto \
  "${prefix}/Library/Frameworks/GStreamer.framework" \
  "${package_root}/lib/GStreamer.framework"

# Match the portable wine-cloud-builder layout: keep only top-level runtime
# dylibs in wine/lib instead of copying whole MacPorts prefixes such as Python.
: > "${runtime_libraries}"
while IFS= read -r runtime_port; do
  while IFS= read -r source_path; do
    source_path="${source_path#${source_path%%[![:space:]]*}}"
    [[ "${source_path}" == "${prefix}/lib/"* ]] || continue

    relative_path="${source_path#"${prefix}/lib/"}"
    [[ "${relative_path}" != */* ]] || continue
    case "${relative_path}" in
      *.dylib|*.so)
        [[ -e "${source_path}" || -L "${source_path}" ]] || continue
        printf '%s\n' "${source_path}" >> "${runtime_libraries}"
        ;;
    esac
  done < <("${port_command}" -q contents "${runtime_port}")
done < "${runtime_ports}"

/usr/bin/sort -u -o "${runtime_libraries}" "${runtime_libraries}"
while IFS= read -r source_path; do
  destination="${package_root}/lib/$(basename "${source_path}")"
  /bin/cp -pP "${source_path}" "${destination}"
done < "${runtime_libraries}"

find "${package_root}" \( -name '.DS_Store' -o -name '._*' \) -delete
/usr/bin/xattr -cr "${package_root}"

/usr/bin/python3 "${script_dir}/relocate-wine-macho.py" \
  "${package_root}" "${prefix}"

printf 'Packaged %s runtime ports and %s top-level runtime libraries.\n' \
  "$(wc -l < "${runtime_ports}" | tr -d ' ')" \
  "$(wc -l < "${runtime_libraries}" | tr -d ' ')"
