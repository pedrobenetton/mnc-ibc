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

Run `uv run ibc --help` for all options.

### Ground-truth metadata (optional)

If you know which state each dataset belongs to (e.g. simulated data), IBC can
compare its clusters against those labels: it prints a per-dataset table and a
cluster-composition matrix, and the projection plot uses a marker shape per label.

Pass the file explicitly with `-M/--metadata`, or name it `metadata.txt`,
`metadata.tsv` or `metadata.csv` and put it in the input folder, where it is
picked up automatically. Without a metadata file, IBC just reports the clusters.

The file has two columns, a dataset ID and a label, one dataset per line:

```text
# dataset   label
101         ground_state
102         ground_state
149         non_ground_state
150         non_ground_state
```

* Columns may be separated by spaces, tabs or commas; text after `#` is ignored.
* Labels are free text without spaces (`ground_state`, `apo`, `ligand_bound`, ...).
* A dataset matches an ID when its file name without `.mtz` equals the ID
  (`101` ↔ `101.mtz`). Otherwise, the number at the end of the name is compared,
  so ID `101` also matches `hTTR_P21212-x101.mtz`.
* Datasets with no entry are reported as `UNKNOWN`; IBC warns about unmatched
  datasets and about entries that matched nothing.

## Layout

```
src/cpp/mtz_reader_py.cpp    C++ MTZ reader + CC matrix (pybind11 module ibc.fast_mtz)
src/ibc/cli.py               pipeline and `ibc` entry point
src/ibc/clustering/          embedding optimisation, elbow detection, OPTICS
src/ibc/utils/               argument parsing, printing, run folders
```