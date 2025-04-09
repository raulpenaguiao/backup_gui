# Compiler Instructions

This guide explains how to use `compiler.py` to create program releases for different operating systems.

## Prerequisites

- Python 3.x installed
- Required dependencies (install via pip):
    ```bash
    pip install pyinstaller
    ```

## Usage

### Windows
```bash
python compiler.py --os windows --version x.x.x
```

### macOS
```bash
python3 compiler.py --os mac --version x.x.x
```

### Linux
```bash
python3 compiler.py --os linux --version x.x.x
```

## Parameters

- `--os`: Target operating system (windows/mac/linux)
- `--version`: Version number for the release (e.g., 1.0.0)

## Output

Compiled releases will be created in the `releases` directory with the following structure:
```
releases/
└── x.x.x/
        └── [os-specific-files]
```