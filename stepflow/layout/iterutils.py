# iterutils.py

from collections.abc import Iterable
from typing import TypeVar, Callable, Iterator, Tuple, List, Optional

T = TypeVar("T")
S = TypeVar("S")

def entries(iterable: Iterable[T]) -> Iterator[Tuple[int, T]]:
    """
    Yield (index, element) pairs from the given iterable, 0-based.
    Similar to TypeScript 'entries'.
    """
    index = 0
    for element in iterable:
        yield (index, element)
        index += 1


def flat_map(iterable: Iterable[T], callback: Callable[[T, int], Iterable[S]]) -> Iterator[S]:
    """
    Python version of TypeScript 'flatMap'.
    For each element x in 'iterable', call 'callback(x, i)' which returns another iterable,
    and yield all items from that iterable.
    """
    for i, element in entries(iterable):
        for sub in callback(element, i):
            yield sub


def reduce_(iterable: Iterable[T], callback: Callable[[S, T, int], S], initial_value: S) -> S:
    """
    Python version of TypeScript 'reduce', but with an index.

    'callback' is a function (acc, current, index) -> newAcc.
    'initial_value' is the initial accumulator.
    """
    accumulator = initial_value
    for i, element in entries(iterable):
        accumulator = callback(accumulator, element, i)
    return accumulator


def map_(iterable: Iterable[T], callback: Callable[[T, int], S]) -> Iterator[S]:
    """
    Python version of TypeScript 'map' that also provides an index.
    """
    for i, element in entries(iterable):
        yield callback(element, i)


def filter_(iterable: Iterable[T], callback: Callable[[T, int], bool]) -> Iterator[T]:
    """
    Python version of TypeScript 'filter' that also provides an index.
    We create our own to pass the index. If you only need 'element', use built-in filter.
    """
    for i, element in entries(iterable):
        if callback(element, i):
            yield element


def some(iterable: Iterable[T], callback: Callable[[T, int], bool]) -> bool:
    """
    Return True if callback(element, index) is True for at least one item.
    """
    for i, element in entries(iterable):
        if callback(element, i):
            return True
    return False


def every(iterable: Iterable[T], callback: Callable[[T, int], bool]) -> bool:
    """
    Return True if callback(element, index) is True for every item.
    """
    for i, element in entries(iterable):
        if not callback(element, i):
            return False
    return True


def length(iterable: Iterable[T]) -> int:
    """
    Return the total number of items in iterable, akin to TS 'length'.
    """
    # Could also do: return sum(1 for _ in iterable)
    count = 0
    for _ in iterable:
        count += 1
    return count


def slice_(arr: List[T], frm: int = 0, to: Optional[int] = None, stride: int = 1) -> Iterator[T]:
    """
    Python version of TypeScript 'slice', returning an iterator rather than a new list.
    If 'to' is None, default to len(arr). 'stride' must not be zero.
    """
    if stride == 0:
        raise ValueError("can't slice with zero stride")
    start = frm
    end = len(arr) if to is None else to

    # emulate TS logic for positive / negative stride
    if stride > 0:
        limit = min(end, len(arr))
        i = start
        while i < limit:
            yield arr[i]
            i += stride
    else:
        limit = max(end, -1)
        i = start
        while i > limit:
            yield arr[i]
            i += stride


def reverse_(arr: List[T]) -> Iterator[T]:
    """
    Python version of TS 'reverse',
    returning an iterator over arr in reversed order.
    Could also use built-in reversed(arr).
    """
    return slice_(arr, len(arr) - 1, -1, -1)


def chain_(*iterables: Iterable[T]) -> Iterator[T]:
    """
    Python version of TS 'chain': yields from multiple iterables in order.
    This is basically itertools.chain, but we define it ourselves for demonstration.
    """
    for it in iterables:
        for x in it:
            yield x


def bigrams(iterable: Iterable[T]) -> Iterator[Tuple[T, T]]:
    """
    Python version of TS 'bigrams': yield pairs of consecutive items.
    """
    it = iter(iterable)
    try:
        first = next(it)
    except StopIteration:
        return
    last = first
    for next_ in it:
        yield (last, next_)
        last = next_


def first(iterable: Iterable[T]) -> Optional[T]:
    """
    Return the first item of the iterable, or None if empty.
    """
    for item in iterable:
        return item
    return None


def is_iterable(obj: object) -> bool:
    """
    Return True if 'obj' is an iterable (has __iter__).
    Roughly akin to TS 'isIterable'.
    """
    return hasattr(obj, '__iter__')


if __name__ == "__main__":
    # Demonstration usage
    data = [10, 20, 30, 40]
    print("entries(data):", list(entries(data))) 
    # -> [(0,10),(1,20),(2,30),(3,40)]

    print("flat_map data->[x, x+1]:",
          list(flat_map(data, lambda x,i: [x, x+1])))
    # -> [10,11,20,21,30,31,40,41]

    r = reduce_(data, lambda acc,val,idx: acc+val, 0)
    print("reduce_ sum =>", r) 
    # -> sum=100

    print("map_ => squared:", list(map_(data, lambda x,i: x*x)))
    # -> [100,400,900,1600]

    print("filter_ => x>15:", list(filter_(data, lambda x,i: x>15)))
    # -> [20,30,40]

    print("some => x>25:", some(data, lambda x,i: x>25))
    # -> True

    print("every => x<50:", every(data, lambda x,i: x<50))
    # -> True

    print("length =>", length(data)) 
    # -> 4

    print("slice_ => from1..3 stride=1:", list(slice_(data,1,3,1)))
    # -> [20,30]

    print("reverse_ =>", list(reverse_(data))) 
    # -> [40,30,20,10]

    print("chain_ => data + [100,200]", list(chain_(data,[100,200])))
    # -> [10,20,30,40,100,200]

    print("bigrams =>", list(bigrams(data))) 
    # -> [(10,20),(20,30),(30,40)]

    print("first =>", first(data))
    # -> 10

    print("is_iterable => data?", is_iterable(data))
    # -> True