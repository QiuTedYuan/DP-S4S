import argparse
import time

import numpy as np

from Dataset import Dataset
from NoiseGen import NoiseGenerator
from S4SS import r2t, dp_s4s, se_whitebox, se_blackbox


def avg(arr):
    arr = sorted(arr)
    res = arr[int(len(arr)*0.2):int(len(arr)*0.8)]
    return sum(res) / len(res)

def run(algorithm: str, data: Dataset, epsilon: float, delta: float, beta: float,
        global_sensitivity: float, sample_rate: float, max_weight: float, c_bound: int, repeats: int):
    sample_results = []
    results = []
    times = []

    for seed in range(repeats):
        print("iter", seed, "...")
        noise_gen = NoiseGenerator(seed)
        start = time.time()

        num_iterations = int(sample_rate * data.num_vertices)

        if algorithm == 'r2t':
            sample_res = data.result
            res = r2t(data, global_sensitivity, epsilon, beta, noise_gen)

        elif algorithm == 'dp_s4s':
            sample_res, res = dp_s4s(data, global_sensitivity, epsilon, beta, noise_gen, sample_rate, max_weight)

        elif algorithm == 'se_blackbox':
            sample_res, res = se_blackbox(data, global_sensitivity, epsilon, delta, beta, noise_gen, num_iterations, c_bound)


        # elif algorithm == 'se_whitebox':
        #     res = se_whitebox(data, global_sensitivity, epsilon, delta, noise_gen, num_iterations, c_bound)


        elif algorithm == 'gs':
            sample_res = data.result
            res = data.result + noise_gen.generate_laplace(global_sensitivity, epsilon)

        else:
            assert False, "invalid algo"

        tm = time.time() - start

        sample_results.append(sample_res)
        results.append(res)
        times.append(tm)

        print(tm, res)

    return avg(abs(np.array(results) - data.result)) / data.result * 100, avg(times), avg(abs(np.array(results) - np.array(sample_results))) / data.result * 100, avg(abs(np.array(sample_results) - data.result)) / data.result * 100

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DP-S4S.')
    parser.add_argument('-i', '--input', required=True, type=str, help='Input file.txt')
    parser.add_argument('-e', '--epsilon', default=1.0, type=float, help='Epsilon')
    parser.add_argument('-d', '--delta', default=0, type=float, help='Delta')
    parser.add_argument('-b', '--beta', default=0.1, type=float, help='Beta')
    parser.add_argument('-g', '--global_sensitivity', default=1024, type=float, help='Global sensitivity')
    parser.add_argument('-c', '--collaborators', default=1024, type=int, help='Collaborators bound')
    parser.add_argument('-w', '--max_weight', default=1., type=float, help='Max weight of each record')
    parser.add_argument('-s', '--sample_rate_inverse', default=10, type=float, help='Sample rate inverse')
    parser.add_argument('-a', '--algorithm', required=True, type=str, choices=['r2t', 'dp_s4s', 'se_blackbox', 'gs'], help='Algorithm')
    parser.add_argument('-r', '--repeats', default=10, type=int, help='Number of repeats')

    args = parser.parse_args()

    dataset = Dataset.from_path(args.input)
    assert max(dataset.values) <= args.max_weight, "The maximum weight is violated."
    print("Data Size: ", len(dataset.edges))
    print("Query Result: ", dataset.result)
    print("DS:", dataset.downward_sensitivity)

    if args.input.endswith('l1.txt'):
        gs = args.max_weight * args.collaborators
    elif args.input.endswith('l2.txt') or args.input.endswith('triangle.txt'):
        gs = args.max_weight * args.collaborators * args.collaborators
    elif args.input.endswith('rectangle.txt'):
        gs = args.max_weight * args.collaborators * args.collaborators * args.collaborators
    else:
        gs = args.global_sensitivity


    err, time, dp_error, sample_error = run(args.algorithm, dataset, args.epsilon, args.delta, args.beta, gs, 1./args.sample_rate_inverse, args.max_weight, args.collaborators, args.repeats)
    print("time", time)
    print("err", err)
    print("dp_error", dp_error)
    print("sample_error", sample_error)
