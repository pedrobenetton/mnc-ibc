"""Type stubs for the compiled fast_mtz extension (built from src/cpp/mtz_reader_py.cpp)."""

import numpy as np
import numpy.typing as npt

class DatasetPayload:
    filename: str
    spacegroup: str
    success: bool
    error_msg: str
    hkl_encoded: list[int]
    i_mean: list[float]
    sig_i_mean: list[float]

class MatrixResult:
    filenames: list[str]
    R: npt.NDArray[np.float32]
    W: npt.NDArray[np.float32]
    N: npt.NDArray[np.float32]

def read_batch(dir_path: str, sg_number: int = 0, num_threads: int = 8) -> list[DatasetPayload]: ...
def compute_cc_matrix(
    dir_path: str,
    sg_number: int = 0,
    use_counts_as_weights: bool = False,
    num_threads: int = 8,
) -> MatrixResult: ...
