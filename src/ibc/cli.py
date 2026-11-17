import os
import re
import sys
import time

import numpy as np

from ibc import fast_mtz

from ibc.clustering.find_elbow import find_elbow
from ibc.clustering.optics_clustering import (
    plot_multidimensional_grid,
    run_optics_clustering,
    plot_multidimensional_grid_annotated,
)
from ibc.clustering.optimize import scan_dimensions
from ibc.utils.print_utils import (
    print_cluster_summary,
    print_phi_table,
    print_separator,
)
from ibc.utils.parse_args import parse_args
from ibc.utils.create_run_folder import create_run_folder

from collections import Counter, defaultdict


METADATA_DEFAULT_NAMES = ("metadata.txt", "metadata.tsv", "metadata.csv")


def find_metadata_file(metadata_arg, input_folder):
    """Return the metadata path to use, or None if there is none.

    An explicit --metadata path must exist. Without it, look for one of
    METADATA_DEFAULT_NAMES inside the input folder.
    """
    if metadata_arg:
        if not os.path.isfile(metadata_arg):
            raise FileNotFoundError(f"Metadata file not found: {metadata_arg}")
        return metadata_arg

    for candidate in METADATA_DEFAULT_NAMES:
        path = os.path.join(input_folder, candidate)
        if os.path.isfile(path):
            return path
    return None


def read_metadata(metadata_path):
    """Read a two-column metadata file into {dataset_id: label}.

    Columns may be separated by whitespace, tabs or commas. Blank lines and
    anything after '#' are ignored. Lines with a single column are skipped.
    """
    metadata = {}
    with open(metadata_path, "r") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = [p for p in re.split(r"[,\s]+", line) if p]
            if len(parts) < 2:
                print(f"Warning: {metadata_path}:{line_number} has no label, skipped.")
                continue
            dataset_id, label = parts[0], parts[1]
            if dataset_id in metadata and metadata[dataset_id] != label:
                print(f"Warning: {dataset_id} listed twice in {metadata_path}; "
                      f"using '{label}'.")
            metadata[dataset_id] = label
    return metadata


def _trailing_number(text):
    match = re.search(r"(\d+)$", text)
    return int(match.group(1)) if match else None


def match_metadata(names, metadata):
    """Return one label per dataset name ("UNKNOWN" when unmatched).

    A dataset matches an ID when the file name without .mtz equals the ID,
    otherwise when both end in the same number (e.g. ID "101" matches
    "hTTR_P21212-x101.mtz").
    """
    by_number = {}
    ambiguous = set()
    for dataset_id, label in metadata.items():
        number = _trailing_number(dataset_id)
        if number is None:
            continue
        if number in by_number and by_number[number][1] != label:
            ambiguous.add(number)
        by_number[number] = (dataset_id, label)

    labels, used_ids = [], set()
    for name in names:
        stem = os.path.splitext(os.path.basename(str(name)))[0]
        if stem in metadata:
            labels.append(metadata[stem])
            used_ids.add(stem)
            continue
        number = _trailing_number(stem)
        if number is not None and number in by_number and number not in ambiguous:
            dataset_id, label = by_number[number]
            labels.append(label)
            used_ids.add(dataset_id)
        else:
            labels.append("UNKNOWN")

    n_unknown = labels.count("UNKNOWN")
    if n_unknown:
        print(f"Warning: {n_unknown} of {len(names)} datasets have no entry in the metadata.")
    unused = len(metadata) - len(used_ids)
    if unused:
        print(f"Warning: {unused} metadata entries did not match any dataset.")
    if ambiguous:
        print(f"Warning: IDs ending in {sorted(ambiguous)} map to different labels; "
              "only exact file-name matches were used for them.")
    return labels


class Logger(object):
    def __init__(self, log_filepath):
        self.terminal = sys.stdout
        self.log = open(log_filepath, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def pipeline_function(
    args,
    input_folder,
    project_name,
    sg_number,
    d_max,
    forced_dimension,
    use_cache,
    force_recalculate,
    minimize_method,
    use_spectral_init,
    buffer_parameter,
    metadata_arg=None,
    num_threads=8,
):
    print_separator("Building correlation matrix via C++")

    project_folder = create_run_folder(project_name)

    log_file_path = os.path.join(project_folder, "pipeline_run.log")
    original_stdout = sys.stdout
    logger = Logger(log_file_path)
    sys.stdout = logger

    try:

        with open(f"{project_folder}/arguments.txt", "w") as f:
            for key, value in vars(args).items():
                f.write(f"{key}: {value}\n")

        cache_file = f"{project_folder}/cc_matrix.npz"

        if use_cache and not force_recalculate and os.path.exists(cache_file):
            print_separator(f"Loading cached correlation matrix from {cache_file}")
            data = np.load(cache_file, allow_pickle=True)
            names = data["names"]
            R = data["R"]
            W = data["W"]
        else:
            start_time_cc = time.perf_counter()

            matrix_result = fast_mtz.compute_cc_matrix(
                dir_path=input_folder,
                sg_number=sg_number,
                use_counts_as_weights=False,
                num_threads=num_threads,
            )

            names = matrix_result.filenames
            R = matrix_result.R
            W = matrix_result.W

            print(f"Datasets loaded and processed: {len(names)}")

            if use_cache:
                np.savez_compressed(cache_file, names=names, R=R, W=W)
                print(f"Saved correlation matrix cache to {cache_file}")

            end_time_cc = time.perf_counter()
            elapsed_time_load = end_time_cc - start_time_cc
            print(
                f"\nTotal time taken for building cc matrix: {elapsed_time_load:.2f} seconds"
            )

        print("\nCorrelation matrix:")
        print(np.array_str(R, precision=3, suppress_small=True))

        print("\nWeight matrix:")
        print(np.array_str(W, precision=3, suppress_small=True))

        print_separator("Scanning embedding dimensions")

        X_vals, phi_vals = scan_dimensions(
            R, minimize_method, use_spectral_init, forced_dimension, d_max=d_max, W=W
        )

        print_phi_table(phi_vals)

        if forced_dimension == 0:
            optimal_d = find_elbow(phi_vals)
            print(f"\nOptimal dimension: {optimal_d}")
            X = X_vals[optimal_d - 1]
            final_phi = phi_vals[optimal_d - 1]
        else:
            print(f"\nUsing dimension {forced_dimension} (forced by input).")
            optimal_d = forced_dimension
            X = X_vals[0]
            final_phi = phi_vals[0]

        print_separator("Final embedding")

        print(f"Embedding shape: {X.shape}")
        print(f"Final Phi: {final_phi:.6f}")

        X = X / np.linalg.norm(X, axis=1, keepdims=True)

        print_separator("Running OPTICS clustering")

        labels, model = run_optics_clustering(X, buffer_parameter)

        print_cluster_summary(labels)

        metadata_path = find_metadata_file(metadata_arg, input_folder)
        names = [str(n) for n in names]

        if metadata_path is None:
            print("\nNo metadata file given or found in the input folder; "
                  "skipping ground-truth comparison.")
            print("\n" + "=" * 60)
            print(f"{'Filename':<35} | {'Assigned Cluster'}")
            print("=" * 60)
            for name, label in sorted(zip(names, labels), key=lambda x: x[0]):
                cluster_str = f"Cluster {label}" if label != -1 else "Noise / Outlier (-1)"
                print(f"{name:<35} | {cluster_str}")
            print("=" * 60)

            plot_multidimensional_grid(X, labels, project_folder)
            return

        print(f"\nUsing metadata file: {metadata_path}")
        ground_truth = match_metadata(names, read_metadata(metadata_path))

        cluster_groups = defaultdict(list)
        type_to_clusters = defaultdict(Counter)

        print("\n" + "=" * 80)
        print(f"{'Filename':<35} | {'Ground Truth State':<20} | {'Assigned Cluster'}")
        print("=" * 80)

        for name, sample_type, label in sorted(
            zip(names, ground_truth, labels), key=lambda x: x[0]
        ):
            cluster_groups[label].append((name, sample_type))
            type_to_clusters[sample_type][label] += 1

            cluster_str = f"Cluster {label}" if label != -1 else "Noise / Outlier (-1)"
            print(f"{name:<35} | {sample_type:<20} | {cluster_str}")

        print("\n" + "=" * 80)
        print("CLUSTER COMPOSITION MATRIX")
        print("=" * 80)
        all_clusters = sorted(cluster_groups.keys())
        header = f"{'Sample Type':<20} | " + " | ".join(
            f"{f'Cluster {c}' if c != -1 else 'Outliers (-1)':<12}" for c in all_clusters
        )
        print(header)
        print("-" * len(header))

        for stype, counts in type_to_clusters.items():
            row = f"{stype:<20} | " + " | ".join(f"{counts[c]:<12}" for c in all_clusters)
            print(row)
        print("=" * 80)

        # ground_truth follows the order of `names`, i.e. the rows of X and labels.
        plot_multidimensional_grid_annotated(X, labels, ground_truth, project_folder)

    finally:
        sys.stdout = original_stdout
        logger.close()


def main():
    args = parse_args()

    use_cache = not args.no_cache
    force_recalculate = args.force_recalculate
    project_name = args.project_name
    sg_number = args.sg_number
    d_max = args.d_max
    minimize_method = args.scan_method
    use_spectral_init = args.use_spectral_init
    input_folder = args.input_folder
    forced_dimension = args.force_dim
    buffer_parameter = args.buffer_parameter
    metadata_arg = args.metadata

    try:
        available_cpus = len(os.sched_getaffinity(0))
    except AttributeError:
        available_cpus = os.cpu_count() or 4

    if metadata_arg and not os.path.isfile(metadata_arg):
        sys.exit(f"ibc: error: metadata file not found: {metadata_arg}")

    os.makedirs(project_name, exist_ok=True)

    start_time = time.perf_counter()

    pipeline_function(
        args,
        input_folder,
        project_name,
        sg_number,
        d_max,
        forced_dimension,
        use_cache,
        force_recalculate,
        minimize_method,
        use_spectral_init,
        buffer_parameter,
        metadata_arg=metadata_arg,
        num_threads=available_cpus,
    )

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    print(f"\nTotal pipeline time taken: {elapsed_time:.2f} seconds")
    print(f"CPUs utilized: {available_cpus}\n")

if __name__ == "__main__":
    main()