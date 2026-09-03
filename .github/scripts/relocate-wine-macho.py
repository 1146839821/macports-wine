#!/usr/bin/env python3

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


SYSTEM_PREFIXES = ("/System/Library/", "/usr/lib/")


def output(*args: str | Path) -> str:
    return subprocess.run(
        [str(arg) for arg in args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout


def command(*args: str | Path) -> None:
    subprocess.run([str(arg) for arg in args], check=True)


def is_macho(path: Path) -> bool:
    return "Mach-O" in output("/usr/bin/file", "-b", path)


def dependencies(path: Path) -> list[str]:
    result: list[str] = []
    for line in output("/usr/bin/otool", "-L", path).splitlines()[1:]:
        value = line.strip()
        if not value or value.endswith(":"):
            continue
        result.append(value.split(" (compatibility version", 1)[0])
    return result


def install_id(path: Path) -> str | None:
    result = output("/usr/bin/otool", "-D", path).splitlines()
    return result[1].strip() if len(result) > 1 else None


def rpaths(path: Path) -> list[str]:
    result: list[str] = []
    waiting_for_path = False
    for line in output("/usr/bin/otool", "-l", path).splitlines():
        fields = line.strip().split()
        if fields == ["cmd", "LC_RPATH"]:
            waiting_for_path = True
        elif waiting_for_path and fields[:1] == ["path"]:
            result.append(fields[1])
            waiting_for_path = False
    return result


def loader_reference(source: Path, destination: Path) -> str:
    relative = os.path.relpath(destination, source.parent)
    return "@loader_path" if relative == "." else f"@loader_path/{relative}"


class Relocator:
    def __init__(self, package_root: Path, prefix: Path) -> None:
        self.package_root = package_root
        self.prefix = prefix
        self.package_lib = package_root / "lib"
        self.gstreamer = self.package_lib / "GStreamer.framework"
        self.macho_files = sorted(
            path
            for path in package_root.rglob("*")
            if path.is_file() and not path.is_symlink() and is_macho(path)
        )
        self.by_name: dict[str, list[Path]] = {}
        for path in self.macho_files:
            self.by_name.setdefault(path.name, []).append(path)

    def staged_path(self, installed: str) -> Path | None:
        value = Path(installed)
        prefix_lib = self.prefix / "lib"
        prefix_gstreamer = (
            self.prefix / "Library" / "Frameworks" / "GStreamer.framework"
        )
        system_gstreamer = Path("/Library/Frameworks/GStreamer.framework")

        try:
            relative = value.relative_to(prefix_lib)
            candidate = self.package_lib / relative
            return candidate if candidate.exists() else None
        except ValueError:
            pass

        for source_root in (prefix_gstreamer, system_gstreamer):
            try:
                relative = value.relative_to(source_root)
                candidate = self.gstreamer / relative
                return candidate if candidate.exists() else None
            except ValueError:
                pass
        return None

    def expand_loader_value(self, path: Path, value: str) -> Path | None:
        if value == "@loader_path":
            return path.parent
        if value.startswith("@loader_path/"):
            return path.parent / value.removeprefix("@loader_path/")
        if value == "@executable_path":
            return self.package_root / "bin"
        if value.startswith("@executable_path/"):
            return self.package_root / "bin" / value.removeprefix(
                "@executable_path/"
            )
        return None

    def resolve_rpath_dependency(
        self, path: Path, dependency: str, current_rpaths: list[str]
    ) -> Path | None:
        suffix = dependency.removeprefix("@rpath/")
        for rpath in current_rpaths:
            directory = self.expand_loader_value(path, rpath)
            if directory is not None:
                candidate = directory / suffix
                if candidate.exists():
                    return candidate

        candidates = self.by_name.get(Path(suffix).name, [])
        exact = [candidate for candidate in candidates if str(candidate).endswith(suffix)]
        if exact:
            candidates = exact
        if not candidates:
            return None

        priorities = (
            path.parent,
            self.package_lib,
            self.package_lib / "wine" / "x86_64-unix",
            self.gstreamer / "Versions" / "1.0" / "lib",
            self.gstreamer / "Libraries",
        )
        for directory in priorities:
            for candidate in candidates:
                if candidate.parent == directory:
                    return candidate
        return sorted(candidates, key=lambda candidate: len(candidate.parts))[0]

    def replace_rpath(
        self, path: Path, old: str, new: str, current_rpaths: list[str]
    ) -> None:
        if old == new:
            return
        if new in current_rpaths:
            command("/usr/bin/install_name_tool", "-delete_rpath", old, path)
            current_rpaths.remove(old)
        else:
            command("/usr/bin/install_name_tool", "-rpath", old, new, path)
            current_rpaths[current_rpaths.index(old)] = new

    def ensure_rpath(
        self, path: Path, directory: Path, current_rpaths: list[str]
    ) -> None:
        value = loader_reference(path, directory)
        if value not in current_rpaths:
            command("/usr/bin/install_name_tool", "-add_rpath", value, path)
            current_rpaths.append(value)

    def relocate_file(self, path: Path) -> None:
        current_id = install_id(path)
        current_rpaths = rpaths(path)

        if current_id and (
            current_id.startswith(str(self.prefix))
            or current_id.startswith("/Library/Frameworks/GStreamer.framework/")
        ):
            current_id = f"@rpath/{path.name}"
            command(
                "/usr/bin/install_name_tool",
                "-id",
                current_id,
                path,
            )

        for old_rpath in list(current_rpaths):
            destination = self.staged_path(old_rpath)
            if destination is not None:
                self.replace_rpath(
                    path,
                    old_rpath,
                    loader_reference(path, destination),
                    current_rpaths,
                )
            elif old_rpath.startswith(str(self.prefix)):
                raise RuntimeError(f"unmapped MacPorts rpath in {path}: {old_rpath}")

        for dependency in dependencies(path):
            if dependency == current_id or dependency.startswith(SYSTEM_PREFIXES):
                continue

            destination: Path | None = None
            if dependency.startswith("@rpath/"):
                destination = self.resolve_rpath_dependency(
                    path, dependency, current_rpaths
                )
                if destination is None:
                    raise RuntimeError(
                        f"unresolved @rpath dependency in {path}: {dependency}"
                    )
            elif dependency.startswith(("@loader_path", "@executable_path")):
                destination = self.expand_loader_value(path, dependency)
                if destination is None or not destination.exists():
                    raise RuntimeError(
                        f"unresolved loader dependency in {path}: {dependency}"
                    )
                continue
            elif dependency.startswith("/"):
                destination = self.staged_path(dependency)
                if destination is None:
                    raise RuntimeError(
                        f"unmapped non-system dependency in {path}: {dependency}"
                    )
                command(
                    "/usr/bin/install_name_tool",
                    "-change",
                    dependency,
                    f"@rpath/{destination.name}",
                    path,
                )
            else:
                raise RuntimeError(f"unknown dependency form in {path}: {dependency}")

            self.ensure_rpath(path, destination.parent, current_rpaths)

        command("/usr/bin/codesign", "--force", "--sign", "-", path)

    def relocate(self) -> None:
        for path in self.macho_files:
            self.relocate_file(path)
        if self.gstreamer.exists():
            command(
                "/usr/bin/codesign",
                "--force",
                "--deep",
                "--sign",
                "-",
                self.gstreamer,
            )

    def audit(self) -> None:
        failures: list[str] = []
        for path in self.macho_files:
            current_id = install_id(path)
            current_rpaths = rpaths(path)
            for value in current_rpaths:
                if value.startswith("/") and not value.startswith(SYSTEM_PREFIXES):
                    failures.append(f"absolute rpath in {path}: {value}")

            for dependency in dependencies(path):
                if dependency == current_id or dependency.startswith(SYSTEM_PREFIXES):
                    continue
                if dependency.startswith("@rpath/"):
                    if self.resolve_rpath_dependency(
                        path, dependency, current_rpaths
                    ) is None:
                        failures.append(
                            f"unresolved @rpath dependency in {path}: {dependency}"
                        )
                elif dependency.startswith(("@loader_path", "@executable_path")):
                    destination = self.expand_loader_value(path, dependency)
                    if destination is None or not destination.exists():
                        failures.append(
                            f"unresolved loader dependency in {path}: {dependency}"
                        )
                elif dependency.startswith("/"):
                    failures.append(f"absolute dependency in {path}: {dependency}")
                else:
                    failures.append(f"unknown dependency in {path}: {dependency}")

            signature = subprocess.run(
                ["/usr/bin/codesign", "--verify", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if signature.returncode:
                failures.append(f"invalid code signature: {path}")

        if failures:
            raise RuntimeError("\n".join(failures))


def main() -> None:
    audit_only = False
    arguments = sys.argv[1:]
    if arguments[:1] == ["--audit"]:
        audit_only = True
        arguments = arguments[1:]
    if len(arguments) != 2:
        raise SystemExit(
            "usage: relocate-wine-macho.py [--audit] <package-root> <prefix>"
        )

    relocator = Relocator(Path(arguments[0]).resolve(), Path(arguments[1]).resolve())
    if audit_only:
        relocator.audit()
    else:
        relocator.relocate()
        relocator.audit()


if __name__ == "__main__":
    main()
