import argparse
import time

import numpy as np

from Dataset import Dataset
from NoiseGen import NoiseGenerator
from R2T import r2t, dp_s4s, se_whitebox, se_blackbox


def avg(arr):
    arr = sorted(arr)
    res = arr[int(len(arr)*0.2):int(len(arr)*0.8)]
    return sum(res) / len(res)

def run(algorithm: str, data: Dataset, epsilon: float, delta: float, beta: float,
        global_sensitivity: float, sample_rate: float, max_weight: float, c_bound: int):
    results = []
    times = []

    for seed in range(100):
        print("iter", seed, "...")
        noise_gen = NoiseGenerator(seed)
        start = time.time()

        num_iterations = int(sample_rate * data.num_vertices)

        res = 0.

        if algorithm == 'r2t':
            res = r2t(data, global_sensitivity, epsilon, beta, noise_gen)

        elif algorithm == 'dp_s4s':
            res = dp_s4s(data, global_sensitivity, epsilon, beta, noise_gen, sample_rate, max_weight)

        elif algorithm == 'se_blackbox':
            res = se_blackbox(data, global_sensitivity, epsilon, delta, beta, noise_gen, num_iterations, c_bound)

        elif algorithm == 'se_whitebox':
            res = se_whitebox(data, global_sensitivity, epsilon, delta, noise_gen, num_iterations, c_bound)

        else:
            assert False, "invalid algo"

        tm = time.time() - start

        results.append(res)
        times.append(tm)

        print(tm, res)

    return avg(abs(np.array(results) - data.result)) / data.result * 100, avg(times)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sample-based R2T.')
    parser.add_argument('-i', '--input', required=True, type=str, help='Input file.txt')
    parser.add_argument('-e', '--epsilon', default=1.0, type=float, help='Epsilon')
    parser.add_argument('-d', '--delta', default=0, type=float, help='Delta')
    parser.add_argument('-b', '--beta', default=0.1, type=float, help='Beta')
    parser.add_argument('-g', '--global_sensitivity', default=1024, type=float, help='Global sensitivity')
    parser.add_argument('-c', '--collaborators', default=1024, type=int, help='Collaborators bound')
    parser.add_argument('-w', '--max_weight', default=1., type=float, help='Max weight of each record')
    parser.add_argument('-s', '--sample_rate_inverse', default=10, type=float, help='Sample rate inverse')
    parser.add_argument('-a', '--algorithm', required=True, type=str, choices=['r2t', 'dp_s4s', 'se_blackbox', 'se_whitebox'], help='Algorithm')

    args = parser.parse_args()

    dataset = Dataset.from_path(args.input)
    assert max(dataset.values) <= args.max_weight, "The maximum weight is violated."
    print("Data Size: ", len(dataset.edges))
    print("Query Result: ", dataset.result)

    if args.input.endswith('l1.txt'):
        gs = args.max_weight * args.collaborators
    elif args.input.endswith('l2.txt') or args.input.endswith('triangle.txt'):
        gs = args.max_weight * args.collaborators * args.collaborators
    elif args.input.endswith('rectangle.txt'):
        gs = args.max_weight * args.collaborators * args.collaborators * args.collaborators
    else:
        gs = args.global_sensitivity


    err, time = run(args.algorithm, dataset, args.epsilon, args.delta, args.beta, gs, 1./args.sample_rate_inverse, args.max_weight, args.collaborators)
    print("time", time)
    print("err", err)
