# setup-blender

Downloads and installs Blender on your GitHub Actions runner, adding Blender to `PATH` so you can call `blender` directly.

```bash
blender --version
```

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
              os: [macos-14, "ubuntu-latest", "windows-latest"]
        steps:
            - uses: actions/checkout@v4
            - name: Install Blender
              uses: bradyajohnston/setup-blender@v3
              with:
                version: ${{ matrix.version }}
            - name: Run tests in Blender
              run: blender --version
```

## Caching

This action automatically caches downloaded Blender archives to speed up subsequent runs. The cache key is based on:
- Operating system (`runner.os`)
- Architecture (`runner.arch`)
- Full Blender version (`FULL_VERSION`)

When the same version is requested on the same platform, the cached download will be restored instead of downloading again. This significantly reduces action runtime and bandwidth usage.

The cache is managed automatically by the action - no configuration is required.

Notes:
- `daily` builds come from the daily builder and are not official releases. Use for testing against upcoming changes.
- If omitted, `version` defaults to `latest`.
