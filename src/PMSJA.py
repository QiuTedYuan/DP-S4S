import logging
import math
import R2T

import cplex
import mosek
import numpy as np

from Dataset import Dataset
from DatasetMultipleQuery import DatasetMultipleQuery
from NoiseGen import NoiseGenerator, PrivacyBudgetAllocator
from Smooth import find_alpha_rho, AdditiveSmoothSensitivity

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class Optimizer(cplex.callbacks.SimplexCallback):
    lower_bound = None

    def __call__(self):
        if self.get_objective_value() < self.lower_bound:
            self.abort()

# records solutions stats for a range of tau values
class LpSolver:
    def __init__(self, dataset: Dataset, base: float, taus):
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

class QCQPSolver:
    def __init__(self, dataset: DatasetMultipleQuery, log_level = logging.INFO):
        self.dataset = dataset

        self.num_yi = self.dataset.num_users()
        self.num_zkj = self.dataset.num_records_total()
        self.log_level = log_level

        self.env = mosek.Env()
        self.env.putlicensepath("../mosek.lic")

    def get_idx_for_z(self, query, record):
        return self.num_yi + self.dataset.get_record_idx(query, record)


    def solve(self, tau):
        num_variables = self.num_yi + self.num_zkj

        with self.env.Task() as task:
            task.set_Stream(mosek.streamtype.log, lambda text: logger.debug(text))
            # variables
            # 0 <= yi  <= 1 for each user
            # 0 <= zkj <= 1 for each query x record
            task.appendvars(num_variables)
            task.putvarboundlist(range(num_variables), [mosek.boundkey.ra] * num_variables,
                                 [0.0] * num_variables, [1.0] * num_variables)
            # objective: maximize sum yi
            task.putobjsense(mosek.objsense.maximize)
            task.putclist(range(self.num_yi), [1.0] * self.num_yi)

            # linear condition: for each record,
            # sum_{i in kj} yi - z_kj <= |users in kj| - 1
            task.appendcons(self.num_zkj)
            for query in range(self.dataset.num_queries()):
                for record in range(self.dataset.num_records_of_query(query)):
                    record_idx = self.dataset.get_record_idx(query, record)
                    record_users = self.dataset.query_records[query][record]
                    asub = []
                    aval = []
                    # sum yi
                    for user in record_users:
                        asub.append(user)
                        aval.append(1.0)
                    # -zkj
                    asub.append(self.get_idx_for_z(query, record))
                    aval.append(-1.0)
                    task.putarow(record_idx, asub, aval)
                    # <= |users| - 1
                    task.putconbound(record_idx, mosek.boundkey.up, 0.0, len(record_users) - 1.0)

            # there is another quadratic condition
            # tau >= sqrt(sum_{k in query} (sum_{records of i} w_{kj} * z_kj)^2) for each i
            # we write it into Fx+g, where each user has a cone containing at most (|query|+1) rows
            # for user i,the first row of F is zero, and for g is tau
            # each of the following row of F corresponds to sum_{records of i} w_{kj}*z_{kj} for query k
            user_cones = {}
            for query in range(self.dataset.num_queries()):
                for record in range(self.dataset.num_records_of_query(query)):
                    for user in self.dataset.query_records[query][record]:
                        if not user in user_cones:
                            user_cones[user] = {}
                        if not query in user_cones[user]:
                            user_cones[user][query] = {}
                        user_cones[user][query][self.get_idx_for_z(query, record)] = self.dataset.query_values[query][record]

            # Construct F matrix in sparse form
            Fsubi = []
            Fsubj = []
            Fval = []
            cone_size_prefix = [0]

            for user in user_cones:
                prefix = cone_size_prefix[-1]
                cone_size_prefix.append(prefix + 1 + len(user_cones[user]))
                for idx, query in enumerate(user_cones[user]):
                    for varidx in user_cones[user][query]:
                        Fsubi.append(prefix + 1 + idx)
                        Fsubj.append(varidx)
                        Fval.append(user_cones[user][query][varidx])

            # Fill in F storage
            task.appendafes(cone_size_prefix[-1])
            task.putafefentrylist(Fsubi, Fsubj, Fval)
            for uid, user in enumerate(user_cones):
                prefix = cone_size_prefix[uid]
                task.putafeg(prefix, tau)

                # Define a conic quadratic domain
                quadDom = task.appendquadraticconedomain(cone_size_prefix[uid+1] - prefix)

                # Create the ACC
                task.appendacc(quadDom,  # Domain index
                               range(prefix, cone_size_prefix[uid+1]),  # Indices of AFE rows [0,...,k]
                               None)  # Ignored

            if self.log_level == logging.DEBUG:
                task.writedata('task_'+str(tau)+'.ptf')
            task.optimize()

            # Extract the solutions
            task.solutionsummary(mosek.streamtype.msg)
            xx = task.getxx(mosek.soltype.itr)
            sum_yi = np.sum(xx[0:self.num_yi])
            logger.debug("tau = " + str(tau))
            logger.debug("sol = " + str(sum_yi))
            logger.debug(task.getsolsta(mosek.soltype.itr))
            return sum_yi, xx


def pmsja(dataset: DatasetMultipleQuery, epsilon: float, delta: float, beta: float, noise_gen: NoiseGenerator):
    base = 2
    solver = QCQPSolver(dataset)
    thres = -20 / epsilon * math.log(1./beta) + dataset.num_users()
    thres_tilde = thres + noise_gen.generate_laplace(20, epsilon)
    E = {}
    I_sol = {}
    noises = {}
    tau = base
    DS = dataset.l2_downward_sensitivity()
    while tau < DS:
        noises[tau] = noise_gen.generate_laplace(40, epsilon)
        tau *= base
    tau /= base
    pre_E = dataset.num_users()
    while tau >= base:
        if pre_E + noises[tau] < thres_tilde:
            E[tau] = thres_tilde - noises[tau] - 1
        else:
            E[tau], I_sol[tau] = solver.solve(tau)
            pre_E = E[tau]
        tau /= base
    tau = base
    while True:
        if tau >= DS:
            E[tau] = dataset.num_users()
            I_sol[tau] = np.ones(dataset.num_users())
            noises[tau] = noise_gen.generate_laplace(40, epsilon)
        if E[tau] + noises[tau] >= thres_tilde:
            E_star = E[tau]
            break
        tau *= base

    # print("tau used: ", tau )

    if tau >= DS:
        truncated_query = dataset.query_results()
    else:
        truncated_query = np.zeros(dataset.num_queries())
        for query in range(dataset.num_queries()):
            for record in range(dataset.num_records_of_query(query)):
                truncated_query[query] += I_sol[tau][solver.get_idx_for_z(query, record)] * dataset.query_values[query][record]

    # print("Truncated: ", truncated_query)

    temp = delta / 2 / math.exp(0.55*epsilon)
    T_hat = 2*(dataset.num_users()-E_star) \
            + noise_gen.generate_laplace(2, 0.45*epsilon) \
            + 2/(0.45*epsilon)*math.log(math.exp(epsilon*0.55)/delta)
    Gauss_noise = T_hat *tau*math.sqrt(2*math.log(1/temp)) * (1+0.45*epsilon/(4*math.log(1/temp))) / (0.45*epsilon) * np.random.normal(0, 1, dataset.num_queries())

    return tau, truncated_query + Gauss_noise



def r2t_multiple_query(dataset: DatasetMultipleQuery, gs: float, epsilon: float, delta: float, beta: float, noise_gen: NoiseGenerator):
    res = np.zeros(dataset.num_queries())
    eps = PrivacyBudgetAllocator.allocate_advanced_composition(dataset.num_queries(), epsilon, delta)
    for query in range(dataset.num_queries()):
        ds_q = Dataset(dataset.query_records[query], dataset.query_values[query])
        #res[query] = R2T.r2t(ds_q, gs, eps, beta / dataset.num_queries(), noise_gen)
        res[query] = R2T.dp_s4s(ds_q, gs, eps, beta / dataset.num_queries(), noise_gen, max_weight=1, sample_rate=0.5)
    return res

def pmsja_renyi(original_dataset: DatasetMultipleQuery, epsilon: float, delta: float, beta: float, noise_gen: NoiseGenerator, sample_rate=1.):
    alpha, rho = find_alpha_rho(epsilon, delta, original_dataset.num_queries())

    if sample_rate < 1.:
        dataset = DatasetMultipleQuery.sample_from(original_dataset, noise_gen, sample_rate)
    else:
        dataset = original_dataset
    base = 2
    tau0 = 1
    solver = QCQPSolver(dataset)
    thres = -20 / epsilon * math.log(1./beta) + dataset.num_users()
    thres_tilde = thres + noise_gen.generate_laplace(20, epsilon)
    E = {}
    I_sol = {}
    u = {}
    tau = tau0
    DS = dataset.l2_downward_sensitivity()
    while tau < DS:
        u[tau] = noise_gen.generate_laplace(40, epsilon)
        tau *= base
    tau /= base
    pre_E = dataset.num_users()
    while tau >= tau0:
        if pre_E + u[tau] < thres_tilde:
            E[tau] = thres_tilde - u[tau] - 1
        else:
            E[tau], I_sol[tau] = solver.solve(tau)
            pre_E = E[tau]
        tau /= base
    tau = tau0
    while True:
        if tau >= DS:
            E[tau] = dataset.num_users()
            I_sol[tau] = np.ones(dataset.num_users())
            u[tau] = noise_gen.generate_laplace(40, epsilon)
        if E[tau] + u[tau] >= thres_tilde:
            E_star = E[tau]
            break
        tau *= base

    if tau >= DS:
        truncated_query = dataset.query_results()
    else:
        truncated_query = np.zeros(dataset.num_queries())
        for query in range(dataset.num_queries()):
            for record in range(dataset.num_records_of_query(query)):
                truncated_query[query] += I_sol[tau][solver.get_idx_for_z(query, record)] * dataset.query_values[query][record]

    logging.debug("Truncated: ", truncated_query)

    ss = AdditiveSmoothSensitivity(2 * tau, alpha, rho, dataset.num_queries())

    noise = ss.sample_noise(dataset.num_users()-E_star)
    return tau, (truncated_query + noise) / sample_rate


def user_sample_pmsja(dataset: DatasetMultipleQuery, epsilon: float, delta: float, beta: float, noise_gen: NoiseGenerator):
    degree_upper_bound = 1024
    node_count = dataset.user_cnt
    num_iterations = 1000

    eps_each_iteration = PrivacyBudgetAllocator.allocate_advanced_composition(num_iterations, epsilon, delta / 2)
    amplified_eps_per_iteration = math.log(1 + node_count / degree_upper_bound * (math.exp(eps_each_iteration) - 1))
    total_res = np.zeros(dataset.num_queries())

    for _ in range(num_iterations):
        sampled_user = noise_gen.randint(node_count)
        sampled_dataset = DatasetMultipleQuery()
        for query in range(len(dataset.query_records)):
            sampled_records = []
            sampled_values = []
            for idx in range(len(dataset.query_records[query])):
                edge = tuple(dataset.query_records[query][idx])
                if edge[0] == sampled_user:
                    sampled_records.append(dataset.query_records[query][idx])
                    sampled_values.append(dataset.query_values[query][idx])
            sampled_dataset.add_query_records(sampled_records, sampled_values)
        tau, res = pmsja_renyi(sampled_dataset, amplified_eps_per_iteration, delta / 2 / num_iterations, beta / num_iterations, noise_gen, 1.)
        total_res = np.add(total_res, res)

    return total_res / num_iterations * node_count
