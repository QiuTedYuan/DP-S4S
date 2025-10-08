import logging
import math

import cplex
import numpy as np
from scipy.special.cython_special import binom

from Dataset import Dataset
from NoiseGen import NoiseGenerator, PrivacyBudgetAllocator

logging.basicConfig(level=logging.INFO)

class Optimizer(cplex.callbacks.SimplexCallback):
    lower_bound = None

    def __call__(self):
        if self.get_objective_value() < self.lower_bound:
            self.abort()


# solutions stats for a range of tau values
class LpSolver:
    def __init__(self, dataset: Dataset, taus: np.ndarray[np.float64]):
        self.dataset = dataset

        self.taus = taus
        self.gs = self.taus[-1]

        self.upper_bounds = np.zeros(len(taus))
        self.is_optimal = np.zeros(len(taus), dtype=bool)

        self.noisy_max = 0.

    def solve(self, idx: int, noise: float):
        if self.is_optimal[idx]:
            return

        if self.taus[idx] >= self.dataset.downward_sensitivity:
            self.upper_bounds[idx] = self.dataset.result
            self.is_optimal[idx] = True
            return

        cpx = cplex.Cplex()
        cpx.objective.set_sense(cpx.objective.sense.maximize)

        num_edges = len(self.dataset.edges)
        obj = np.ones(num_edges)
        ub = np.array(self.dataset.values)
        cpx.variables.add(obj=obj, ub=ub)

        rhs = np.ones(self.dataset.num_vertices) * self.taus[idx]
        senses = "L" * self.dataset.num_vertices
        cpx.linear_constraints.add(rhs=rhs, senses=senses)

        cols = []
        rows = []
        vals = []
        for edge_idx in range(num_edges):
            for user_idx in self.dataset.edges[edge_idx]:
                cols.append(edge_idx)
                rows.append(user_idx)
                vals.append(1)
        cpx.linear_constraints.set_coefficients(zip(rows, cols, vals))
        cpx.set_log_stream(None)
        cpx.set_error_stream(None)
        cpx.set_warning_stream(None)
        cpx.set_results_stream(None)

        cpx.parameters.lpmethod.set(cpx.parameters.lpmethod.values.dual)

        optimizer = cpx.register_callback(Optimizer)
        optimizer.lower_bound = self.noisy_max - noise

        cpx.solve()

        self.upper_bounds[idx] = cpx.solution.get_objective_value()
        if cpx.solution.get_status() == cpx.solution.status.optimal:
            self.is_optimal[idx] = True

base = 5.5

def r2t(dataset: Dataset, gs: float, epsilon: float, beta: float, noise_gen: NoiseGenerator, delta:float=0):
    num_taus = int(math.log(gs, base)) + 1
    taus = np.power(base, list(range(num_taus)))
    lp_solver = LpSolver(dataset, taus)

    for idx in reversed(range(num_taus)):
        tau = lp_solver.taus[idx]
        if delta == 0:
            noise = noise_gen.generate_negative_laplace(
                sensitivity=tau, epsilon=epsilon / num_taus, beta=beta / num_taus)
        else:
            noise = noise_gen.generate_negative_gaussian(
                sigma=NoiseGenerator.gaussian_sigma_adp(tau, epsilon / num_taus, delta / num_taus), beta=beta / num_taus)
        lp_solver.solve(idx, noise)
        if lp_solver.is_optimal[idx]:
            if lp_solver.upper_bounds[idx] + noise >= lp_solver.noisy_max:
                lp_solver.noisy_max = lp_solver.upper_bounds[idx] + noise

    return lp_solver.noisy_max

def sample_r2t_trivial(dataset: Dataset, gs: float, epsilon: float, beta: float, noise_gen: NoiseGenerator, sample_rate):
    sample_dataset = Dataset.sample_from(dataset, noise_gen, sample_rate)
    return r2t(sample_dataset, gs, epsilon, beta, noise_gen) / sample_rate


def dp_s4s(dataset: Dataset, gs: float, epsilon: float, beta: float, noise_gen: NoiseGenerator, sample_rate, max_weight):
    if sample_rate == 1:
        sample_dataset = dataset
    else:
        sample_dataset = Dataset.sample_and_normalize_from(dataset, noise_gen, sample_rate, max_weight)
    gs = gs / max_weight

    num_taus = int(math.log(gs, base)) + 1
    taus: np.ndarray[np.float64] = np.power(base, list(range(num_taus)))
    lp_solver = LpSolver(sample_dataset, taus)
    budget_allocator = PrivacyBudgetAllocator(taus, sample_rate)
    epsilons = budget_allocator.allocate(epsilon)

    for idx in reversed(range(num_taus)):
        noise = noise_gen.generate_negative_laplace(sensitivity=lp_solver.taus[idx],
                                                    epsilon=epsilons[idx], beta = beta / num_taus)
        lp_solver.solve(idx, noise)
        if lp_solver.is_optimal[idx]:
            if lp_solver.upper_bounds[idx] + noise >= lp_solver.noisy_max:
                lp_solver.noisy_max = lp_solver.upper_bounds[idx] + noise

    return lp_solver.noisy_max / sample_rate * max_weight


def se_whitebox(dataset: Dataset, gs: float, epsilon: float, delta: float, noise_gen: NoiseGenerator, k, c_bound):
    node_count = dataset.num_vertices

    if delta > 0:
        eps_each_iteration = PrivacyBudgetAllocator.allocate_advanced_composition(k, epsilon, delta)
    else:
        eps_each_iteration = epsilon / k

    amplified_eps_per_iteration = math.log(1 + node_count / c_bound * (math.exp(eps_each_iteration) - 1))

    num_taus = int(math.log(gs, base)) + 1
    taus = np.power(base, list(range(num_taus)))

    record_counts = {}
    for edge in dataset.edges:
        record_counts[edge[0]] = record_counts.get(edge[0], 0) + 1

    results = []
    for tau in taus:
        res = 0.
        for _ in range(k):
            sampled_user = noise_gen.randint(node_count)
            actual = record_counts.get(sampled_user, 0)
            res += min(actual, tau) + noise_gen.generate_laplace(tau, amplified_eps_per_iteration)
        results.append(res / k * node_count)

    best_idx = -1
    best_result = 0
    min_err = abs(best_result - dataset.result)
    for idx in range(num_taus):
        result = results[idx]
        if abs(result - dataset.result) < min_err:
            min_err = abs(result - dataset.result)
            best_result = result
            best_idx = idx

    print("best tau: ", taus[best_idx])

    return best_result

def se_blackbox(dataset: Dataset, gs: float, epsilon: float, delta: float, beta: float, noise_gen: NoiseGenerator, k, c_bound):
    node_count = dataset.num_vertices

    if node_count - k * c_bound < k:
        prob_no_collaborator = 0
    else:
        prob_no_collaborator = binom(node_count - k * c_bound, k) / binom(node_count, k)

    print("prob", 1-prob_no_collaborator)
    assert delta == 0, "approx DP currently unsupported"

    amplified_eps = math.log(1 + (math.exp(epsilon) - 1) / (1 - prob_no_collaborator))
    amplified_delta = delta

    sampled_instance = Dataset.sample_explore(dataset, noise_gen, k)

    return r2t(sampled_instance, gs, amplified_eps, beta, noise_gen, amplified_delta)/ k * node_count




