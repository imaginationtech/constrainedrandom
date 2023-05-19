# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

from collections import defaultdict
from functools import partial

import constraint
import random


# The maximum iterations before giving up on any randomisation
MAX_ITERATIONS = 100
# The largest domain size to use with the constraint library
CONSTRAINT_MAX_DOMAIN_SIZE = 1 << 10


class Random(random.Random):
    '''
    Seeded, repeatable, deterministic random object. Ideally one of these should be used per seeded
    random activity.

    Subclass of random.Random, enhanced with some quality-of-life features.
    '''

    def weighted_choice(self, choices_dict):
        return self.choices(tuple(choices_dict.keys()), weights=tuple(choices_dict.values()))

    def dist(self, dist_dict):
        answer = self.weighted_choice(choices_dict=dist_dict)[0]
        if isinstance(answer, range):
            return self.randrange(answer.start, answer.stop)
        return answer


class RandVar:
    '''
    Randomisable variable. For internal use with RandObj.
    '''

    def __init__(self, parent, name, order, *, domain=None, bits=None, fn=None, args=None, constraints=None, max_iterations=MAX_ITERATIONS):
        self.parent = parent
        self.random = self.parent._random
        self.name = name
        self.order = order
        self.max_iterations = max_iterations
        assert  ((domain is not None) != (fn is not None)) != (bits is not None), "Must specify exactly one of fn, domain or bits"
        if fn is None:
            assert args is None, "args has no effect without fn"
        self.domain = domain
        self.bits = bits
        self.fn = fn
        self.args = args
        self.constraints = constraints if constraints is not None else []
        if not (isinstance(self.constraints, tuple) or isinstance(self.constraints, list)):
            self.constraints = (self.constraints,)
        # Default strategy is to randomize and check the constraints.
        self.check_constraints = len(self.constraints) > 0
        # Create a function, self.randomizer, that returns the appropriate random value
        if self.fn is not None:
            if self.args is not None:
                self.randomizer = partial(self.fn, *self.args)
            else:
                self.randomizer = self.fn
        elif self.bits is not None:
            self.randomizer = partial(self.random.getrandbits, self.bits)
            self.domain = range(0, 1 << self.bits)
        else:
            # If we are provided a sufficiently small domain and we have constraints, simply construct a
            # constraint solution problem instead.
            is_range = isinstance(self.domain, range)
            is_list = isinstance(self.domain, list) or isinstance(self.domain, tuple)
            is_dict = isinstance(self.domain, dict)
            if self.check_constraints and len(self.domain) < CONSTRAINT_MAX_DOMAIN_SIZE and (is_range or is_list):
                problem = constraint.Problem()
                problem.addVariable(self.name, self.domain)
                for con in self.constraints:
                    problem.addConstraint(con, (self.name,))
                # Produces a list of dictionaries
                solutions = problem.getSolutions()
                def solution_picker(solns):
                    return self.random.choice(solns)[self.name]
                self.randomizer = partial(solution_picker, solutions)
                self.check_constraints = False
            elif is_range:
                self.randomizer = partial(self.random.randrange, self.domain.start, self.domain.stop)
            elif is_list:
                self.randomizer = partial(self.random.choice, self.domain)
            elif is_dict:
                self.randomizer = partial(self.random.dist, self.domain)
            else:
                raise TypeError(f'RandVar was passed a domain of a bad type - {self.domain}. Domain should be a range, list, tuple or dictionary.')

    def randomize(self):
        value = self.randomizer()
        okay = not self.check_constraints
        iterations = 0
        while not okay:
            if iterations == self.max_iterations:
                raise RuntimeError("Too many iterations, can't solve problem")
            problem = constraint.Problem()
            problem.addVariable(self.name, (value,))
            for con in self.constraints:
                problem.addConstraint(con, (self.name,))
            okay = problem.getSolution() is not None
            if not okay:
                value = self.randomizer()
            iterations += 1
        return value


class MultiVarProblem:
    '''
    Multi-variable problem.

    Used internally by RandObj. Represents one problem concerning multiple random variables.
    '''

    def __init__(self, parent, vars, constraints, max_iterations=MAX_ITERATIONS):
        self.parent = parent
        self.random = self.parent._random
        self.vars = vars
        self.constraints = constraints
        self.max_iterations = max_iterations

    def determine_order(self):
        '''
        Chooses an order in which to resolve the values of the variables.
        '''
        # Aim to build a list of lists, each inner list denoting a group of variables
        # to solve at the same time.
        # The best case is to simply solve them all at once, if possible, however it is
        # likely that the domain will be too large.

        # Use order hints first, remaining variables can be placed anywhere the domain
        # isn't too large.
        sorted_vars = sorted(self.vars.values(), key=lambda x: x.order)

        # Currently this is just a flat list. Group into as large groups as possible.
        result = [[sorted_vars[0]]]
        index = 0
        domain_size = len(sorted_vars[0].domain) if sorted_vars[0].domain is not None else 1
        for var in sorted_vars[1:]:
            if var.domain is not None:
                domain_size = domain_size * len(var.domain)
            if var.order == result[index][0].order and domain_size < CONSTRAINT_MAX_DOMAIN_SIZE:
                # Put it in the same group as the previous one, carry on
                result[index].append(var)
            else:
                # Make a new group
                index += 1
                domain_size = len(var.domain) if var.domain is not None else 1
                result.append([var])

        return result

    def _solve(self, groups, max_iterations, solutions_per_group=None):
        '''
        Constraint solving algorithm (internally used by MultiVarProblem).

        If solutions_per_group is not None, solve one constraint group problem 'sparsely',
        i.e. keep only a subset of potential solutions between groups.
        Fast but prone to failure.
        solutions_per_group = 1 is effectively a depth-first search through the state space
        and comes with greater benefits of considering each multi-variable constraint at
        most once.

        If solutions_per_group is None, Solve constraint problem 'thoroughly',
        i.e. keep all possible results between iterations.
        Slow, but will usually converge.
        '''

        constraints = self.constraints
        sparse_solver = solutions_per_group is not None

        if sparse_solver:
            solved_vars = defaultdict(set)
        else:
            solved_vars = []
            problem = constraint.Problem()

        for idx, group in enumerate(groups):
            # Construct a constraint problem where possible. A variable must have a domain
            # in order to be part of the problem. If it doesn't have one, it must just be
            # randomized.
            if sparse_solver:
                # Construct one problem per iteration, add solved variables from previous groups
                problem = constraint.Problem()
                for name, values in solved_vars.items():
                    problem.addVariable(name, list(values))
            group_vars = []
            rand_vars = []
            for var in group:
                group_vars.append(var.name)
                if var.domain is not None and not isinstance(var.domain, dict):
                    problem.addVariable(var.name, var.domain)
                    # If variable has its own constraints, these must be added to the problem,
                    # regardless of whether var.check_constraints is true, as the var's value will
                    # depend on the value of the other constrained variables in the problem.
                    for con in var.constraints:
                        problem.addConstraint(con, (var.name,))
                else:
                    rand_vars.append(var)
            # Add all pertinent constraints
            skipped_constraints = []
            for (con, vars) in constraints:
                skip = False
                for var in vars:
                    if var not in group_vars and var not in solved_vars:
                        # Skip this constraint
                        skip = True
                        break
                if skip:
                    skipped_constraints.append((con, vars))
                    continue
                problem.addConstraint(con, vars)
            # Problem is ready to solve, apart from any new random variables
            solutions = []
            attempts = 0
            while True:
                if attempts >= max_iterations:
                    # We have failed, give up
                    return None
                for var in rand_vars:
                    # Add random variables in with a concrete value
                    if solutions_per_group > 1:
                        var_domain = set()
                        for _ in range(solutions_per_group):
                            var_domain.add(var.randomize())
                        problem.addVariable(var.name, list(var_domain))
                    else:
                        problem.addVariable(var.name, (var.randomize(),))
                solutions = problem.getSolutions()
                if len(solutions) > 0:
                    break
                else:
                    attempts += 1
                    for var in rand_vars:
                        # Remove from problem, they will be re-added with different concrete values
                        del problem._variables[var.name]
            # This group is solved, move on to the next group.
            if sparse_solver:
                if idx != len(groups) - 1:
                    # Store a small number of concrete solutions to avoid bloating the state space.
                    if solutions_per_group < len(solutions):
                        solution_subset = self.random.choices(solutions, k=solutions_per_group)
                    else:
                        solution_subset = solutions
                    solved_vars = defaultdict(set)
                    for soln in solution_subset:
                        for name, value in soln.items():
                            solved_vars[name].add(value)
                if solutions_per_group == 1:
                    # This means we have exactly one solution for the variables considered so far,
                    # meaning we don't need to re-apply solved constraints for future groups.
                    constraints = skipped_constraints
            else:
                solved_vars += group_vars

        return self.random.choice(solutions)

    def solve(self):
        '''
        Attempt to solve the variables with respect to the constraints.
        '''
        groups = self.determine_order()

        solution = None

        # Try to solve sparsely first
        sparsities = [1, 10, 100, 1000]
        for sparsity in sparsities:
            for _ in range(self.max_iterations // 10):
                solution = self._solve(groups, self.max_iterations // 10, sparsity)
                if solution is not None and len(solution) > 0:
                    return solution

        # Try 'thorough' method - no backup plan if this fails
        solution = self._solve(groups)
        if solution is None:
            raise RuntimeError("Could not solve problem.")
        return solution


class RandObj:
    '''
    Randomisable object.
    
    Goal: Implements everything that would be expected from an SV randomisable object.
    '''

    def __init__(self, random, *, max_iterations=MAX_ITERATIONS):
        '''
        seed:            What seed to use for randomisation.
        max_iterations:  The maximum number of attempts to solve a problem before giving up.
        '''
        # Prefix 'internal use' variables with '_', as randomised results are populated to the class
        self._random = random
        self._random_vars = {}
        self._constraints = []
        self._constrained_vars = set()
        self._max_iterations = max_iterations
        self._naive_solve = True

    def set_naive_solve(self, naive: bool):
        '''
        Disable/enable naive solving step, i.e. randomising and checking constraints.
        For some problems, it is more expedient to skip this step and go straight to
        a MultiVarProblem.
        '''
        self._naive_solve = naive

    def add_rand_var(self, name, domain=None, bits=None, fn=None, args=None, constraints=None, order=0):
        '''
        Add a random variable to the object.

        name:   The name of the variable.

        Exactly one of domain, bits, or fn (optionally with args) must be provided to determine
        how to randomise.

        domain:       range, list, tuple or dictionary, specifying possible values to randomly select from.
        bits:         int specifying a bit width to randomise.
        fn:           The function to be called to supply the value of the variable. Typically from Random.
        args:         A tuple of arguments supplied to the function fn.
        constraints:  List of constraints applying to a single variable. Arbitrary function accepting one argument that returns True/False.
        order:        Index to determine what order to resolve the variables.
        '''
        # Check this is a valid name
        assert name not in self.__dict__, f"random variable name {name} is not valid, already exists in object"
        assert name not in self._random_vars, f"random variable name {name} is not valid, already exists in random variables"
        self._random_vars[name] = RandVar(parent=self, name=name, domain=domain, bits=bits, fn=fn, args=args, constraints=constraints, order=order)

    def add_multi_var_constraint(self, _constraint, variables):
        '''
        Add an aribtrary constraint to more than one variable.

        _constraint:  A function (or callable) that accepts the variables as an argument and returns either True or False.
                      If the function returns True when passed the variables, the constraint is satisfied.
        variables:    A tuple/list of variables affected by this constraint.
        '''
        for var in variables:
            assert var in self._random_vars, f"Variable {var} was not in the set of random variables!"
            self._constrained_vars.add(var)
        self._constraints.append((_constraint, variables))

    def pre_randomize(self):
        '''
        Called by randomize before randomizing variables. Can be overridden to do something.
        '''


    def randomize(self):
        '''
        Randomizes all random variables (in self._random_vars), applying constraints provided (in self._constraints).
        '''
        self.pre_randomize()

        result = {}

        for name, random_var in self._random_vars.items():
            result[name] = random_var.randomize()

        # If there are constraints, first try just to solve naively by randomising the values.
        # This will be faster than constructing a MultiVarProblem if the constraints turn out
        # to be trivial. Only try this a few times so as not to waste time.
        constraints_satisfied = len(self._constraints) == 0
        if self._naive_solve:
            attempts = 0
            max = self._max_iterations
            while not constraints_satisfied:
                if attempts == max:
                    break
                problem = constraint.Problem()
                for var in self._constrained_vars:
                    problem.addVariable(var, (result[var],))
                for _constraint, variables in self._constraints:
                    problem.addConstraint(_constraint, variables)
                solutions = problem.getSolutions()
                if len(solutions) > 0:
                    # At least one solution was found, all is well
                    constraints_satisfied = True
                    solution = self._random.choice(solutions)
                    result.update(solution)
                else:
                    # No solution found, re-randomise and try again
                    for var in self._constrained_vars:
                        result[var] = self._random_vars[var].randomize()
                    attempts += 1

        # If constraints are still not satisfied by this point, construct a multi-variable
        # problem and solve them properly
        if not constraints_satisfied:
            multi_var_problem = MultiVarProblem(self, {name: var for name, var in self._random_vars.items() if name in self._constrained_vars}, self._constraints)
            result.update(multi_var_problem.solve())

        # Update this object such that the results of randomisation are available as member variables
        self.__dict__.update(result)

        self.post_randomize()

    def post_randomize(self):
        '''
        Called by randomize after randomizing variables. Can be overridden to do something.
        '''

    def get_results(self):
        '''
        Returns a dictionary of the results from the most recent randomization.
        This is mainly provided for testing purposes.

        Note that individual variables can be accessed as member variables of
        a RandObj instance once randomized, e.g.
        rand = Random(0)
        randobj = RandObj(rand)
        randobj.add_rand_var('a', domain=range(10))
        randobj.randomize()
        print(randobj.a)
        '''
        try:
            # Return a new dict object rather than a reference to this object's __dict__
            return {k: self.__dict__[k] for k in self._random_vars.keys()}
        except KeyError as e:
            raise RuntimeError("Can't call .get_results() until .randomize() has been called at least once.")
