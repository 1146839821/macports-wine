# Endfield FineWine patches

These files were copied from:

- Repository: https://github.com/stoicswe/Endfield_FineWine
- Commit: `e5d4ccad235eefe32d912733e57e4c0bb53a5b58`
- Source directories: `patches/stage1-macos` and `patches/stage2-dwproton`
- License: LGPL-2.1-or-later

The upstream patch order is `stage2-dwproton/em-backports`, then
`stage2-dwproton/misc`, followed by the two `stage1-macos` patches.

All 23 upstream patch files are vendored here. The em-backports set targets
CrossOver 26.2's Wine 11.0 source: changes `0001` and `0002` are already present
in Wine 11.8, while `0003` through `0017` are applied through the matching
Wine 11.8 forward ports already stored under `../dwproton/0001-em-backports`.
The Portfile applies all four imported misc patches and macOS patch `0000`
directly. The `wine-11.8` directory contains the minimal context rebase of
macOS patch `0001`, needed because the existing WineHQ bug 56441 patch inserts
an additional handler between the upstream context lines. This preserves the
complete original source set without applying any change twice.
