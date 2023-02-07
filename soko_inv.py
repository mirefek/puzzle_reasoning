import os
from soko_enc import *
from helpers import *

def boxes_state(state, *boxes, sk = None, nsk = None, vals = None, comp_block = None):
    if sk is not None or nsk is not None:
        assert not (sk is None and nsk is None)
        if sk is None:
            sk = nsk
            sk_negated = True
        else:
            sk_negated = False
        available = ~state.level.walls
        for box in boxes:
            available[box] = False
        if comp_block:
            if isinstance(comp_block[0], numbers.Integral):
                comp_block = [comp_block]
            for pos in comp_block:
                available[pos] = False
        sk = component2d(available, *sk)
        cond_sk = reduce_or(state.sk[sk])
        if sk_negated: cond_sk = neg(cond_sk)
    else:
        cond_sk = True
    cond_boxes = reduce_and(
        state.boxes[box]
        for box in boxes
    )
    return cond_sk & cond_boxes

def simple_deadlocks(state, vals = None):
    reachable = np.zeros_like(state.level.storages)
    stack = list(positions_true(state.level.storages))
    while stack:
        pos = stack.pop()
        if reachable[pos]: continue
        reachable[pos] = True
        for d in directions:
            pos2 = move_pos(pos, d)
            if not state.level.available_pos(pos2): continue
            pos3 = move_pos(pos2, d)
            if not state.level.available_pos(pos3): continue
            stack.append(pos2)
    unreachable = ~(state.level.walls | reachable)
    cond_single = reduce_or(
        state.boxes[unreachable]
    )
    cond_squares = False
    end_resolved = state.level.walls | state.level.storages
    for y in range(state.level.height-1):
        for x in range(state.level.width-1):
            if unreachable[y:y+2,x:x+2].any(): continue
            if end_resolved[y:y+2,x:x+2].all(): continue
            sq_walls = state.level.walls[y:y+2,x:x+2]
            if sq_walls.sum() > 2: continue
            if sq_walls.sum() == 2 and sq_walls[0,0] == sq_walls[1,1]: continue
            cur_square = reduce_and(
                state.boxes[y:y+2,x:x+2][~sq_walls]
            )
            cond_squares = cond_squares | cur_square
    return cond_single | cond_squares

def cave_right_upper(state):
    left =  (state.boxes[7,7] & neg(state.sk[7,8])) | state.boxes[7,8]
    left = left & state.boxes[8,8]
    left = left & neg(state.sk[7,9]) & neg(state.sk[8,9])
    blocked = left & state.boxes[7,9]
    left = left | state.boxes[7,9]
    right = state.boxes[9,11] & state.boxes[8,12] & neg(state.sk[8,11])
    right = (right | state.boxes[8,11]) & state.boxes[7,12]
    right = (right & neg(state.sk[7,11])) | state.boxes[7,11]
    right = right | (
        boxes_state(
            state,
            (9,11), (9,12),
            nsk = (8,12),
            comp_block = (7,10),
        ) & (
            state.boxes[7,12] | state.boxes[8,12]
        )
    )
    return reduce_or(
        left & right & neg(state.sk[7,10]),
        left & state.boxes[7,10],
        right & state.boxes[7,10],
        blocked,
    )

def cave_right_bottom(state):
    left = reduce_and(state.boxes[9,7:9])
    left = left | reduce_and(
        state.boxes[8,7:9],
        reduce_or(state.boxes[9,7:9]),
        neg(reduce_or(state.sk[9,7:9])),
    )
    right = reduce_and(state.boxes[9,11:13])
    right = right | reduce_and(
        state.boxes[8,11], state.boxes[9,12],
        neg(state.sk[9,11]),
    )
    right = right | boxes_state(
        state,
        (8,11), (8,12), (7,12),
        nsk = (9,12),
        comp_block = [(10,11),(10,12)],
    )
    right = right | boxes_state(
        state,
        (9,11), (8,12), (7,12),
        nsk = (9,12),
        comp_block = [(10,11),(10,12)],
    )
    mask = np.zeros(state.level.size, dtype = bool)
    mask[7:10,11:14] = True
    mask[7,11] = False
    right = right | reduce_and(
        neg(at_most(state.boxes[mask])[1]),
        neg(reduce_or(state.sk[mask])),
        reduce_or(
            state.boxes[7,11],
            state.boxes[7,10] & neg(state.sk[7,11]),
            state.boxes[7,9] & neg(state.sk[7,10]) & neg(state.sk[7,11]),
        )
    )
    return reduce_and(
        left, right, neg(reduce_or(state.sk[10,7:13]))
    )

def cave_right(state, vals = None):
    box_count_mask = np.zeros(state.level.size, dtype = bool)
    box_count_mask[7:11,7:14] = True
    box_count_mask &= ~state.level.walls
    box_count_mask[7:9,7] = False
    nsk_mask = np.array(box_count_mask, dtype = bool)
    box_count_mask[7:9,8] = False
    cnt = at_most(state.boxes[box_count_mask])
    nsk = neg(reduce_or(state.sk[nsk_mask]))
    cave_start = reduce_and(
        state.boxes[7,7] | state.boxes[7,8],
        state.boxes[8,7] | state.boxes[8,8],
        neg(cnt[3]) | (neg(cnt[2]) & state.boxes[8,7] & state.boxes[8,8]),
        nsk,
    )
    nsk_mask = np.array(box_count_mask, dtype = bool)

    # cave_start = cave_start | reduce_and(
    #     state.boxes[8,6],
    #     state.boxes[8,7],
    #     state.boxes[7,7] | state.boxes[7,8],
    #     neg(cnt[2]),
    #     nsk,
    # )

    res = cave_start | cave_right_upper(state) | cave_right_bottom(state)
    return res

def cave_up(state, vals = None):
    res_A = boxes_state(
        state,
        (2,5), (4,5), (6,5), (6,6),
        nsk = (4,6),
    )
    res_B = reduce_and(
        reduce_or(state.boxes[4:6,5]),
        reduce_or(state.boxes[4:6,6]),
        reduce_or(state.boxes[2:4,5]),
        boxes_state(
            state,
            nsk = (3,5),
            comp_block = [(5,5), (5,6)],
        ),
    )
    res_C = reduce_and(
        reduce_or(state.boxes[2:4,5]),
        reduce_or(state.boxes[2:4,6]),
        boxes_state(
            state,
            nsk = (1,5),
            comp_block = [(3,5), (3,6)],
        ),
    )
    return res_A | res_B | res_C

def cave_left_upper(state):
    res = state.boxes[6,3]
    for i in range(5,1,-1):
        res = res & state.boxes[i,2] & neg(state.sk[i,3])
        if i > 2: res = res | state.boxes[i,3]
    res = neg(reduce_or(state.sk[1,2:4])) & (res | (
        state.boxes[3,2] & state.boxes[2,3] & neg(state.sk[2,2])
    ))
    res = res | boxes_state(state, (2,2), (2,3), nsk = (1,2))
    res = res | boxes_state(state, (3,2), (3,3), nsk = (1,2))
    return res

def cave_left(state, vals = None):
    cond = cave_left_upper(state)
    mask = np.zeros_like(state.level.walls)
    mask[1:9,1:4] = True
    mask &= ~state.level.walls
    mask2 = np.array(mask)
    mask[7,3] = False
    if vals is not None:
        x = reduce_or(
            state.boxes[7,3],
            neg(state.sk[7,3]) & reduce_or(
                state.boxes[7,4],
                neg(state.sk[7,4]) & state.boxes[7,5] & state.boxes[6,5],
            ),
        )
        y = at_least(state.boxes[mask])[4]

    cond = cond | reduce_and(
        neg(reduce_or(state.sk[mask])),
        reduce_or(
            reduce_and(
                at_least(state.boxes[mask])[4],
                reduce_or(
                    state.boxes[7,3],
                    neg(state.sk[7,3]) & reduce_or(
                        state.boxes[7,4],
                        reduce_and(
                            neg(state.sk[7,4]),
                            state.boxes[7,5],
                            reduce_or(
                                state.boxes[6,5],
                                neg(state.sk[8,5]) & state.boxes[8,6],
                            )
                        )
                    ),
                ),
            ),
            state.boxes[7,3] & state.boxes[7,4],
        )
    )
    mask[7,2] = False
    cond = cond | reduce_and(
        state.boxes[7,2],
        at_least(state.boxes[mask])[4],
    )
    cond = cond | boxes_state(state, (6,2), (7,2))
    cond = cond | boxes_state(state, (6,3), (7,2), sk = (6,2))
    cond = cond | boxes_state(state, (7,2), (7,3), sk = (6,2))
    cond = cond | reduce_and(
        at_least(state.boxes[2:7,2:4].flat)[5],
        (
            boxes_state(state, nsk = (3,3), comp_block = [(6,2), (6,3)])
            | (neg(state.boxes[6,3]) & neg(state.boxes[5,3]) &
               state.sk[5,3]
            )
        )
    )
    cond = cond | reduce_and(
        neg(reduce_or(state.sk[4:6,3])),
        reduce_and(
            state.boxes[4:6,2],
            reduce_or(state.boxes[3:5,3]),
            reduce_or(state.boxes[5:7,3]),
        )
    )
    cond = cond | reduce_and(
        neg(reduce_or(state.sk[3:7,1])),
        state.boxes[3:7,2],
    )
    return cond

def specific_deadlocks(state, vals):
    res = reduce_or(
        reduce_and(
            reduce_or(state.boxes[2:4,2]),
            reduce_or(state.boxes[2:4,3]),
            neg(reduce_or(state.sk[1:3,2:4])),
        ),
        reduce_and(
            boxes_state(
                state,
                (7,5), (6,6),
                sk = (7,6),
            ),
            at_least(state.boxes[1:6,5])[2],
            at_least(state.boxes[1:9,1:5].flat)[4],
        ),
        cave_up(state),
        cave_right(state, vals),
        cave_left(state, vals),
    )
    box_count_mask = np.zeros(state.level.size, dtype = bool)
    box_count_mask[7:11,7:14] = True
    box_count_mask[7,6] = True
    box_count_mask &= ~state.level.walls
    res = res | reduce_and(
        boxes_state(state, (2,5), (4,5), (6,5), (7,5), sk = (7,4)),
        at_least(state.boxes[box_count_mask])[5],
        at_most(state.boxes[8,6:9])[2],
    )
    if vals is not None: print(vals[res])
    res = res | boxes_state(
        state,
        (2,5), (4,5), (6,5), (7,6), (7,7),
        sk = (7,4),
    )
    if vals is not None: print(vals[res])
    # res = res | boxes_state(
    #     state,
    #     (2,5), (4,5), (6,5), (7,7), (7,8),
    #     sk = (7,4),
    # )

    return res

def inv26(state, vals = None):
    unreachable = reduce_and(state.boxes[8:10, 12])
    ini_boxes = np.array(state.level.boxes)
    ini_boxes[3:5,8] = False
    ini_boxes = positions_true(ini_boxes)
    sk = state.level.storekeeper
    ini = reduce_or(
        boxes_state(state, (3,8), (4,8), *ini_boxes, sk = sk),
        boxes_state(state, (4,7), *ini_boxes, sk = sk, vals = vals),
        boxes_state(state, (4,6), *ini_boxes, sk = sk),
    )
    mask = np.zeros_like(state.level.boxes)
    mask[:,:6] = True
    mask[7:,:] = True
    mask &= ~state.level.walls
    cond = neg(at_most(state.boxes[mask])[11])
    mask[7:,7:] = False
    cond = cond & at_least(state.boxes[mask])[7]
    mask[:,:] = 0
    mask[2:8,5] = True
    mask[8,6] = True
    cond = cond & reduce_and(
        at_least(state.boxes[mask])[3],
        implies(
            state.boxes[7,5],
            (
                boxes_state(state, nsk = (5,2), comp_block = (7,5)) |
                at_most(state.boxes[2:8,2:6].flat)[3]
            )
        ),
    )
    cond = cond & implies(
        at_most(state.boxes[2:8,5].flat)[2],
        at_least(state.boxes[2:8,2:5].flat)[4],
        neg(reduce_or(
            state.boxes[7,6],
            boxes_state(state, (7,7), (8,6), nsk = (8,7))
        )),
    )
    cond = cond & implies(
        state.boxes[7,6],
        boxes_state(state, nsk = (6,6), comp_block = [(7,5), (7,6)]),
    )
    cond = cond & neg(reduce_and(
        boxes_state(state, (7,4), sk = (7,3)),
        at_least(state.boxes[2:8,2:4].flat)[4],
    ))
    cond = cond & at_most(state.boxes[8:10,6:9].flat)[2]
    cond = cond & neg(reduce_and(state.boxes[7,6:8]))
    cond = cond | simple_deadlocks(state, vals) | ini | specific_deadlocks(state, vals)
    return cond & neg(unreachable)
    
if __name__ == "__main__":

    full_fname = "./soko_unsolvable.xsb"
    levels = SokoLevel.all_from_file(full_fname)
    level = levels[0]
    print("Level:", full_fname)
    check_invariant(level, inv26, debug = True)
    print("This invariant is not finished yet, it is expected that it is not working.")
