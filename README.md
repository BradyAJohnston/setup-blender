# setup-blender

Downloads and installs Blender to path on your GHA runner, so you can just call `blender` without having to worry about installation.

```bash
blender --version
```

## Versions

Versions can be specified with or without the patch version, as well as "daily" for the latest daily alpha builds being worked on.

Examples: 
 - `4.2`: will be expanded to the latest `4.2.x` release (currently `4.2.6`)
 - `4.3.2`: will fetch this exact version
 - `daily`: will fetch the latest daily build alpha build from https://builder.blender.org/download/daily/

Exmaple workflow which gets blender for 3 different versions on 3 different operating systems, and then uses Blender to print the version to the console:
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
              version: ["4.2", "4.3.2", "daily"]
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
