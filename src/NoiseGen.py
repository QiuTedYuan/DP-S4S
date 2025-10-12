import math
from functools import cache

import numpy as np
import sklearn
from numpy._typing import NDArray
from scipy.special import logsumexp
from scipy.stats import binom


class NoiseGenerator:
    def __init__(self, seed):
        self.random_state = sklearn.utils.check_random_state(seed)

    def generate_laplace(self, sensitivity: float, epsilon: float):
        return self.random_state.laplace(loc=0, scale=sensitivity/epsilon)

    @staticmethod
    def laplace_tail_inverse(sensitivity: float, epsilon: float, beta: float):
        return sensitivity / epsilon * np.log(1. / beta)

    def generate_negative_laplace(self, sensitivity: float, epsilon: float, beta: float):
        return self.generate_laplace(sensitivity=sensitivity, epsilon=epsilon) - self.laplace_tail_inverse(sensitivity=sensitivity, epsilon=epsilon, beta=beta)

    @staticmethod
    def gaussian_sigma_rdp(sensitivity, alpha, epsilon):
        return sensitivity * np.sqrt(alpha / 2. / epsilon)

    @staticmethod
    def gaussian_sigma_adp(sensitivity, epsilon, delta):
        return sensitivity * np.sqrt(2. * np.log(1.25 / delta)) / epsilon

    def generate_gaussian(self, sigma):
        return self.random_state.normal(loc=0, scale=sigma)

    @staticmethod
    def gaussian_tail_inverse(sigma: float, beta: float):
        return sigma * np.sqrt(2. * np.log(2. / beta))

    def generate_negative_gaussian(self, sigma, beta):
        return self.generate_gaussian(sigma=sigma) - self.gaussian_tail_inverse(sigma=sigma, beta=beta)

    def randint(self, ub):
        return self.random_state.randint(ub)

    def uniform(self, low, high):
        return self.random_state.uniform(low, high)

    def random_sample(self, size):
        return self.random_state.random_sample(size)

    def choice(self, a, size, replace, p=None):
        return self.random_state.choice(a, size, replace, p)

def binary_search(left, right, func, target, accuracy = 10 ** -5):
    while right - left > accuracy:
        mid = (left + right) / 2
        if func(mid) > target:
            right = mid
        else:
            left = mid
    return left

# allocate the privacy budgets for k mechanisms so that the composed mechanism is DP
class PrivacyBudgetAllocator:
    def __init__(self, taus, sample_rate):
        self.taus = taus
        self.q = sample_rate

    @staticmethod
    def allocate_basic_composition(k: int, epsilon: float):
        return epsilon/k

    @staticmethod
    def allocate_advanced_composition(k: int, epsilon: float, delta: float):
        def func(eps):
            return eps * math.sqrt(2 * k * math.log(1/delta)) + k * eps * (math.exp(eps) - 1) / (math.exp(eps) + 1)
        return binary_search(0, epsilon, func, epsilon)

    @staticmethod
    def allocate_user_amplification(k: int, epsilon: float, delta: float, node_count: int, c_bound: int):
        if node_count - k * c_bound < k:
            prob_no_collaborator = 0
        else:
            prob_no_collaborator = binom(node_count - k * c_bound, k) / binom(node_count, k)

        if delta == 0:
            amplified_eps = math.log(1 + (math.exp(epsilon) - 1) / (1 - prob_no_collaborator))
            amplified_delta = 0
        else:
            amplified_eps = 0.5 * math.log(1 + (math.exp(epsilon) - 1) / (1 - prob_no_collaborator))
            amplified_delta = delta / (math.exp(amplified_eps) + 1) / (1 - prob_no_collaborator)
        return amplified_eps, amplified_delta

    @cache
    def allocate(self, epsilon: float):
        remaining = epsilon
        epsilons: NDArray[np.float64] = np.zeros(len(self.taus))
        for idx in reversed(range(len(self.taus))):
            epsilons[idx] = float(remaining / (idx + 1))
            remaining -= self.compute_pure(epsilons[idx], self.taus[idx], self.q, int(self.taus[-1]))
        return epsilons

    @staticmethod
    @cache
    def compute_pure(epsilon: float, tau: float, q: float, delta: float):
        A1 = 1-q+q*np.exp(-epsilon / tau)
        A2 = 1-q+q*np.exp(epsilon / tau)
        q1 = q * np.exp(-epsilon / tau) / A1
        q2 = q * np.exp(epsilon / tau) / A2
        logs1 = binom.logcdf(tau, delta, q1) + delta * np.log(A1)
        logs2 = binom.logcdf(tau, delta, q2) + delta * np.log(A2)
        logs3 = binom.logsf(tau, delta, q) - epsilon
        logs4 = binom.logsf(tau, delta, q) + epsilon
        return max(-logsumexp([logs1, logs3]), logsumexp([logs2, logs4]))
