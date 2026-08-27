# setup-blender

Downloads and installs Blender on your GitHub Actions runner, adding Blender to `PATH` so you can call `blender` directly.

```bash
blender --version
```

## Versioning

Pin to the major tag (`bradyajohnston/setup-blender@v5`) — it always points at the latest `v5.x` release, so you get updates automatically without bumping the version. Pin an exact tag (e.g. `@v5.1`) only if you need to freeze a specific release.

## Inputs: version

Accepts a semantic version or special keywords:

- `4.2`: Expands to the latest `4.2.x` release.
- `4.3.2`: Installs this exact release.
- `daily`: Installs the latest daily build from https://builder.blender.org/download/daily/.
- `latest`: Installs the latest currently released Blender version (stable release).

The action also sets helpful environment variables:

- `BLENDER_BASE_VERSION`: Base series (e.g. `4.2`).
- `FULL_VERSION`: Full version resolved (e.g. `4.2.6`).
- `IS_DAILY`: `true` if using a daily build, otherwise `false`.
- `CACHE_VERSION`: The version component of the cache key (see [Caching](#caching)).
- Daily builds only: `BLEND_URL_WINDOWS_X64`, `BLEND_URL_WINDOWS_ARM64`, `BLEND_URL_MACOS_X64`, `BLEND_URL_MACOS_ARM64`, `BLEND_URL_LINUX_X64`.

Example workflow installing Blender for multiple versions across OSes, then printing the version:
```yaml
name: Run Tests

on: 
    push:
      branches: ["main"]
    pull_request:
      branches: ["*"]
    
jobs:
    build:
        runs-on: ${{ matrix.os }}
        strategy:
            max-parallel: 4
            fail-fast: false
            matrix:
              version: ["latest", "4.2", "daily"]
              os: [macos-latest, "ubuntu-latest", "windows-latest"]
        steps:
            - uses: actions/checkout@v5
            - name: Install Blender
              uses: bradyajohnston/setup-blender@v5
              with:
                version: ${{ matrix.version }}
            - name: Run tests in Blender
              run: blender --version
```

## Caching

This action automatically caches downloaded Blender archives to speed up subsequent runs. The cache key is based on:
- Operating system (`runner.os`)
- Architecture (`runner.arch`)
- `CACHE_VERSION`, which is the full Blender version for releases (e.g. `4.2.6`), and the version plus the build hash for daily builds (e.g. `5.3.0-16f3180fba1e`)

The build hash matters because every daily in a series reports the same version. Keying on the version alone would match the first daily ever cached and keep restoring it, so `version: daily` would silently test a build that is weeks or months old. Including the hash means a new daily is a new key, and each platform is keyed on the hash of the build it actually downloads — the builder does not always publish every platform from the same commit.

When the same version is requested on the same platform, the cached download will be restored instead of downloading again. This significantly reduces action runtime and bandwidth usage.

The cache is managed automatically by the action - no configuration is required. If the build hash for a daily cannot be determined, caching is skipped for that run so a fresh build is always downloaded.

Notes:
- `daily` builds come from the daily builder and are not official releases. Use for testing against upcoming changes.
- If omitted, `version` defaults to `latest`.
