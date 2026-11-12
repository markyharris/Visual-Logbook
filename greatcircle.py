#!/usr/bin/env python3
"""Great-circle distance in nautical miles between two airport
dicts ({"lat", "lon"} in degrees)."""
import math

R_NM = 3440.065


def nm(a, b):
    la1, lo1 = math.radians(a["lat"]), math.radians(a["lon"])
    la2, lo2 = math.radians(b["lat"]), math.radians(b["lon"])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2)
         * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R_NM * math.asin(min(1.0, math.sqrt(h)))
