from django.db import models


class Quantize(models.Func):
    """
    ST_QuantizeCoordinates determines the number of bits (N)
    required to represent a coordinate value with a specified number
    of digits after the decimal point, and then sets all but the N
    most significant bits to zero. The resulting coordinate value will
    still round to the original value, but will have improved compressiblity
    """

    function = "ST_QuantizeCoordinates"
    template = "%(function)s(%(expressions)s, %(quantize)s)"


class Simplify(models.Func):
    """
    Returns a "simplified" version of the given geometry using the Douglas-Peucker algorithm.
    """

    function = "ST_SIMPLIFY"
    template = "%(function)s(%(expressions)s, %(simplify)s)"


class SimplifyPreserve(models.Func):
    """
    Returns a "simplified" version of the given geometry using the Douglas-Peucker algorithm.
    """

    function = "ST_SIMPLIFYPRESERVETOPOLOGY"
    template = "%(function)s(%(expressions)s, %(simplify)s)"
