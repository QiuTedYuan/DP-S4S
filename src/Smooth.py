import numpy as np
from scipy.optimize import brentq


def solve_gamma(alpha, rho, d):
    A = np.exp(rho * (alpha - 1) / d)

    def f(x):
        return x ** alpha - alpha * A * x + (alpha - 1) * A

    t1 = brentq(f, (alpha-1) / alpha, 1)
    t2 = brentq(f,1, np.pow(alpha * A, 1. / (alpha-1)))
    return 0.5 * np.log(min(1. / t1, t2))

def find_alpha_rho(eps, delta, d):
    L = np.log(1. / delta)
    err_star = np.inf
    alpha_star = 0
    rho_star = 0
    for rho in np.arange(0.00001, eps, 0.00001):
        alpha = 1 + L / (eps - rho)
        gamma = solve_gamma(alpha,rho,d)
        err = np.sqrt(alpha / rho) / (1 - alpha + alpha * np.exp(-2 * gamma))
        if err < err_star:
            alpha_star = alpha
            rho_star = rho
            err_star = err
        else:
            break
    return alpha_star, rho_star

class AdditiveSmoothSensitivity:
    def __init__(self, scale, alpha, rho, d):
        self.scale = scale
        self.alpha = alpha
        self.rho = rho
        self.d = d
        self.gamma = solve_gamma(self.alpha, self.rho, self.d)
        self.factor = 1. / (1 - alpha + alpha * np.exp(-2 * self.gamma))

    def compute_g(self, s):
        opt_k = 1. / self.gamma - s
        k = np.floor(opt_k)
        res1 = (k + s) * np.exp(- self.gamma * k)
        k = k + 1
        res2 = (k + s) * np.exp(- self.gamma * k)
        return max(res1, res2)

    def sample_noise(self, s):
        g = self.compute_g(s)
        return np.random.normal(0, 1, size = self.d) * g * np.sqrt(self.alpha / self.rho) * self.scale * self.factor
