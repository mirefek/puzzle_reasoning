from helpers import print_vcenter
from formula import *
from solver import solve

class GameState(BoolObject):
    _level_to_state_class = dict()
    def __init_subclass__(cls, level = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if level is not None:
            GameState._level_to_state_class[level] = cls

    def __init__(self, *args, **kwargs):
        BoolObject.__init__(self, *args, **kwargs)

    @staticmethod
    def from_level(level):
        state_class = GameState._level_to_state_class[type(level)]
        return state_class(level)

def invariant_counterexample(level, invariant, init_in = True, goal_out = True):
    state1 = GameState.from_level(level)
    state2 = GameState.from_level(level)
    cond = state1.is_correct & state2.is_correct
    state1_in = invariant(state1)
    state2_out = neg(invariant(state2))
    if init_in: option_init = state2.is_init & state2_out
    else: option_init = False
    if goal_out: option_goal = state1.is_goal & state1_in
    else: option_goal = False
    option_transition = state1.transition(state2) & state1_in & state2_out
    cond = cond & (option_init | option_goal | option_transition)
    sol = solve(cond)
    if sol is None: return None
    if sol(option_init): return sol, "init", state2
    elif sol(option_goal): return sol, "goal", state1
    elif sol(option_transition): return sol, "transition", (state1, state2)
    else:
        raise Exception("Solution not consistent")

def check_invariant(level, invariant, debug = False, **kwargs):
    example = invariant_counterexample(level, invariant, **kwargs)
    if example is None:
        print("Invariant verified!")
        return True
    else:
        sol, ex_type, state = example
        if ex_type == "init":
            print("Initial state not included")
            print(sol(state))
            if debug: invariant(sol(state))
        elif ex_type == "goal":
            print("Goal state is included")
            print(sol(state))
            if debug: invariant(sol(state))
        elif ex_type == "transition":
            print("Not closed under transitions")
            state1, state2 = state
            print_vcenter(sol(state1), ' ---> ', sol(state2))
            if debug:
                print("State1")
                invariant(sol(state1))
                print("State2")
                invariant(sol(state2))
        else:
            raise Exception(f"Unexpected example type '{ex_type}'")
        return False

def check_init_move(level):
    state1 = GameState.from_level(level)
    state2 = GameState.from_level(level)
    cond = state1.is_correct & state2.is_correct
    cond = cond & state1.is_init
    cond = cond & state1.transition(state2)

    sol = solve(cond)
    if sol is not None:
        print("Example transition:")
        print_vcenter(sol(state1), ' ---> ', sol(state2))
    else:
        print("No initial move available")

def check_limited_solvable(level, num_moves, states_in_row = 4):
    states = [
        GameState.from_level(level)
        for _ in range(num_moves+1)
    ]
    cond = reduce_and(
        state.is_correct for state in states
    )
    cond = cond & states[0].is_init & states[-1].is_goal
    cond = cond & reduce_and(
        state1.transition(state2)
        for state1, state2 in zip(states[:-1], states[1:])
    )
    print(f"Searching for solution in {num_moves} moves")
    sol = solve(cond)
    if sol is not None:
        print("Solution found!")
        for i in range(0, len(states), states_in_row):
            cur_states_in_row = min(states_in_row, len(states)-i)
            row = ['-->']*(2*cur_states_in_row)
            if i + cur_states_in_row >= len(states):
                row.pop() # don't print the last arrow
            for j in range(cur_states_in_row):
                row[2*j] = sol(states[i+j])
            print_vcenter(*row)
            print()
    else:
        print(f"No solution in {num_moves} moves exists")
