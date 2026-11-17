from collections import Counter

def print_separator(title=None):

    print("\n" + "=" * 80)

    if title is not None:
        print(title)

    print("=" * 80)

def print_phi_table(phi_vals, forced_dimension):

    print("\nDimension Scan:")
    print("-" * 30)
    print(f"{'Dim':>5} {'Phi':>15}")

    if forced_dimension != 0:
        print(f"{forced_dimension:>5} {phi_vals[0]:>15.6f}")
        return
    for i, phi in enumerate(phi_vals, start=1):
        print(f"{i:>5} {phi:>15.6f}")

def print_cluster_summary(labels):

    counts = Counter(labels)

    print("\nCluster Summary:")
    print("-" * 30)

    for cluster_id, count in sorted(counts.items()):

        if cluster_id == -1:
            print(f"Outliers : {count}")
        else:
            print(f"Cluster {cluster_id}: {count}")