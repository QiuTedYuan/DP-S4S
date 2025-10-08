import itertools
import subprocess
import os

# Path to your executable or script
PROGRAM = "python3"

# Parameter options
sample_rates = [4,8,16,32,64]
algorithms = ['dp_s4s', 'se_blackbox']
datasets = ['deezer', 'amazon1', 'amazon2']
queries = ['l1', 'l2', 'triangle', 'rectangle']

# Output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Iterate over all parameter combinations
for dataset, query, algorithm, sample_rate in itertools.product(datasets, queries, algorithms, sample_rates):
    # Build command
    cmd = [
        PROGRAM,
        "../src/main.py",
        f"-i ../info/{dataset}/{query}.txt",
        f"-a {algorithm}",
        f"-s {sample_rate}"
    ]

    # Generate output file name
    out_file = os.path.join(output_dir, f"{dataset}_{query}_{algorithm}_{sample_rate}.txt")

    print(f"Running: {' '.join(cmd)} -> {out_file}")

    # Run and redirect output to file
    with open(out_file, "w") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)