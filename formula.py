import numpy as np
import itertools

# used for count_le / count_exact
class LazyArray:
    def __init__(self, size, index_to_value):
        self.index_to_value = index_to_value
        self.undefined = object()
        self.data = [self.undefined]*size
    def __getitem__(self, i):
        res = self.data[i]
        if res is not self.undefined: return res
        res = self.index_to_value(i)
        self.data[i] = res
        return res
    def append(self, x):
        self.data.append(x)
    def __len__(self):
        return len(self.data)
    def __iter__(self):
        i = 0
        while i < len(self.data):
            yield self[i]

class BoolFormula:
    def __or__(self, other):
        if isinstance(other, bool_types):
            if other: return True
            else: return self
        elif other is self: return self
        else: return BoolOr(self, other)
    def __and__(self, other):
        return neg(neg(self) | neg(other))
    def __xor__(self, other):
        if isinstance(other, bool_types):
            if other: return neg(self)
            else: return self
        elif other is self: return False
        else: return ite(self, neg(other), other)
    def equals(self, other):
        if isinstance(other, bool_types):
            if other: return self
            else: return neg(self)
        elif other is self: return True
        else: return ite(self, other, neg(other))

    def __ror__(self, other):
        return self.__or__(other)
    def __rand__(self, other):
        return self.__and__(other)
    def __rxor__(self, other):
        return self.__xor__(other)

bool_types = (bool, np.bool_)
bool_fml_types = bool_types + (BoolFormula,)

class BoolVar(BoolFormula):
    pass
class BoolNeg(BoolFormula):
    __slots__ = ['a']
    def __init__(self, a):
        assert isinstance(a, BoolFormula), type(a)
        self.a = a
class BoolOr(BoolFormula):
    __slots__ = ['a', 'b']
    def __init__(self, a, b):
        assert isinstance(a, BoolFormula)
        assert isinstance(b, BoolFormula)
        self.a = a
        self.b = b

def neg(a):
    if isinstance(a, bool_types): return not a
    elif isinstance(a, BoolNeg): return a.a
    else: return BoolNeg(a)
def ite(c,a,b):
    return (c & a) | (neg(c) & b)

def reduce_boolop(op, zero, data):
    if isinstance(data, bool_fml_types): return data
    if isinstance(data, np.ndarray) and data.ndim != 1:
        data = data.flat
    data = iter(data)
    try:
        res = reduce_boolop(op, zero, next(data))
    except StopIteration:
        return zero
    for x in data:
        res = op(res, reduce_boolop(op, zero, x))
    return res

def reduce_or(*args):
    return reduce_boolop(lambda a,b: a | b, False, args)
def reduce_and(*args):
    return reduce_boolop(lambda a,b: a & b, True, args)

def exactly_one_q(data):
    return reduce_and(
        neg(x) | neg(y)
        for x,y in combinations(data, 2)
    ) & reduce_or(data)        

def exactly_one_l(data):
    found = False
    exceeded = False
    for x in data:
        exceeded = exceeded | (found & x)
        found = found | x
    return found & neg(exceeded)

def one_hot_to_rev_unary(data):
    res = []
    found = False
    exceeded = False
    for x in data:
        exceeded = exceeded | (found & x)
        found = found | x
        res.append(found)
    success = neg(exceeded) & res.pop()
    return res, success

def exactly_one(data):
    if len(data) <= 4: return exactly_one_q(data)
    else: return exactly_one_l(data)

def count_le(data): # [sum(data) <= k for k in range(len(data))]
    if len(data) == 0: return []
    if len(data) == 1: return [neg(data[0])]
    n = len(data) // 2
    count1 = count_le(data[:n])
    count2 = count_le(data[n:])
    count1.append(True)
    count2.append(True)
    return LazyArray(
        len(data),
        lambda k: reduce_or(
            count1[k1] & count2[k-k1]
            for k1 in range(max(0,k+n-len(data)), min(n+1, k+1))
        )
    )

def count_ge(data): # [sum(data) >= k for k in range(len(data)+1)]
    cle = count_le(data)
    return LazyArray(
        len(data)+1,
        lambda k: True if k == 0 else neg(cle[k-1])
    )

at_most  = count_le
at_least = count_ge

def count_exact(data): # [sum(data) == k for k in range(len(data)+1)]
    if len(data) == 0: return [True]
    if len(data) == 1: return [neg(data[0]), data[0]]
    n = len(data) // 2
    count1 = count_exact(data[:n])
    count2 = count_exact(data[n:])
    return LazyArray(
        len(data)+1,
        lambda k: reduce_or(
            count1[k1] & count2[k-k1]
            for k1 in range(max(0,k+n-len(data)), min(n+1, k+1))
        )
    )

def dep_equal(data1, data2):
    if isinstance(data1, (tuple, list, np.ndarray)):
        assert len(data1) == len(data2), (len(data1), len(data2))
        return reduce_and(dep_equal(x1, x2) for x1,x2 in zip(data1, data2))
    else:
        assert isinstance(data1, bool_fml_types)
        assert isinstance(data2, bool_fml_types)
        if isinstance(data1, BoolFormula):
            return data1.equals(data2)
        elif isinstance(data2, BoolFormula):
            return data2.equals(data1)
        else:
            return data1 == data2

def implies(*args):
    res = args[-1]
    for arg in args[:-1]:
        res |= neg(arg)
    return res

if __name__ == "__main__":
    lits = [BoolVar() for _ in range(3)]
    x = reduce_and(lits)
    print(x)
