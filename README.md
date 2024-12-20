# setup-blender

Downloads and installs Blender to path, so you can just call `blender` from the termin on Mac / Linux / Windows:

```bash
blender --version
```

Exmaple:
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
              version: ["4.2", "4.3"]
              os: [macos-14, "ubuntu-latest", "windows-latest"]
        steps:
            - uses: actions/checkout@v4
            - name: Install Blender
              uses: bradyajohnston/setup-blender@v2
              with:
                version: ${{ matrix.version }}
            - name: Run tests in Blender
              run: blender --version
```
