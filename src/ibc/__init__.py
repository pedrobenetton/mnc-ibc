"""Intensity-based clustering of isomorphous multi-crystal MX data sets."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ibc")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "unknown"
