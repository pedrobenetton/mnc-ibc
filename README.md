# IBC
Intensity Based Clustering of isomorphous multi-crystal MX data sets.

## Installation

You need [uv](https://docs.astral.sh/uv/) and a C++17 compiler (`g++` or `clang++`).
gemmi does **not** need to be installed: the build downloads
[gemmi](https://github.com/project-gemmi/gemmi), compiles it as a static library and
links it into the `fast_mtz` extension.

```bash
git clone <repo-url> && cd IBC
uv sync                  # creates .venv, installs dependencies, compiles fast_mtz
uv run ibc --help
```

The first build takes a few minutes (gemmi is compiled once and cached in `build/`).
After editing `src/cpp/mtz_reader_py.cpp`, the next `uv run`/`uv sync` rebuilds it.

To install the `ibc` command globally (outside a project venv):

```bash
uv tool install git+<repo-url>
```

### Build options

* Link against a gemmi you already have installed (e.g. in `~/.local`):

  ```bash
  uv sync --reinstall-package ibc -C cmake.define.IBC_USE_SYSTEM_GEMMI=ON
  ```

* Download a different gemmi release: `-C cmake.define.IBC_GEMMI_VERSION=0.7.4`
* macOS: Apple clang has no OpenMP. Run `brew install libomp` for multi-threading;
  without it the extension still builds but runs single-threaded.

## Usage

```bash
uv run ibc -i path/to/mtz_folder -p my_project
# equivalently: uv run python -m ibc ...
```

## Layout

```
src/cpp/mtz_reader_py.cpp    C++ MTZ reader + CC matrix (pybind11 module ibc.fast_mtz)
src/ibc/cli.py               pipeline and `ibc` entry point
src/ibc/clustering/          embedding optimisation, elbow detection, OPTICS
src/ibc/utils/               argument parsing, printing, run folders
```
