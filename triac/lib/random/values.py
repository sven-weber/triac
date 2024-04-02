BOOLEANS = [True, False]


def probability_bound(prob: float) -> float:
    return min(max(prob, 0), 100)
