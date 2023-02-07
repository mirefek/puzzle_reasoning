from pysat.solvers import Solver
from formula import *
from collections import defaultdict

class Solution(dict):
    def __init__(self, data):
        self.d = dict(data)
        self._np_vectorized = np.vectorize(lambda x: self, otypes = [bool])
    def __call__(self, fml):
        if isinstance(fml, BoolFormula):
            res = self.d.get(fml, None)
            if res is not None: return res
            if isinstance(fml, BoolOr):
                res = self(fml.a) or self(fml.b)
            elif isinstance(fml, BoolNeg):
                res = not self(fml.a)
            elif isinstance(fml, BoolVar):
                res = False
            else: raise Exception(f"Unexpected BoolFormula: {type(fml)}")
            self.d[fml] = res
            return res
        else:
            if fml == True: return True
            elif fml == False: return False
            elif isinstance(fml, (list, tuple)):
                return type(fml)(self(x) for x in fml)
            elif isinstance(fml, np.ndarray):
                return self._np_vectorized(fml)
            elif isinstance(fml, BoolObject):
                return fml.instantiate(self)
            else: raise Exception(f"Undefined solution for {type(fml)}")

def solve(formula):
    if isinstance(formula, bool_types):
        if formula: return dict()
        else: return None
    else:
        with Solver() as solver:
            last_var = 1
            fml_to_var = {formula : 1}
            var_to_fml = {1 : formula}
            solver.add_clause([1])
            stack = [formula]
            def get_var(fml):
                nonlocal last_var
                res = fml_to_var.get(fml, None)
                if res is not None: return res
                stack.append(fml)
                last_var += 1
                var_to_fml[last_var] = fml
                fml_to_var[fml] = last_var
                return last_var
            while stack:
                fml = stack.pop()
                if isinstance(fml, BoolVar):
                    continue # no further constraints
                elif isinstance(fml, BoolNeg):
                    v0 = fml_to_var[fml]
                    v1 = get_var(fml.a)
                    solver.add_clause([v0, v1])
                    solver.add_clause([-v0, -v1])
                elif isinstance(fml, BoolOr):
                    v0 = fml_to_var[fml]
                    v1 = get_var(fml.a)
                    v2 = get_var(fml.b)
                    solver.add_clause([-v0, v1, v2])
                    solver.add_clause([v0, -v1])
                    solver.add_clause([v0, -v2])
            #print(f"Solving: {last_var} variables...")
            if solver.solve():
                return Solution(
                    (var_to_fml[abs(v)], (v > 0))
                    for v in solver.get_model()
                )
            else:
                return None

if __name__ == "__main__":
    lits = [BoolVar() for _ in range(10)]
    xs = count_le(lits)
    print(xs)
    fml = (xs[5] & neg(xs[4])) & count_exact(lits)[5]
    sol = solve(fml)
    print(sol(lits))
