import random

# Generate a random list with 500 values between 1500 and 2500
random_values = [random.randint(1500, 2500) for _ in range(500)]

# Function to find local maxima
def find_local_maxima(values):
    local_maxima = [0] * len(values)
    for i in range(1, len(values) - 1):
        if values[i] > values[i - 1] and values[i] > values[i + 1]:
            local_maxima[i] = values[i]
    return local_maxima

# Function to find local minima
def find_local_minima(values):
    local_minima = [0] * len(values)
    for i in range(1, len(values) - 1):
        if values[i] < values[i - 1] and values[i] < values[i + 1]:
            local_minima[i] = values[i]
    return local_minima

# Function to find stability intervals
def find_stability_intervals(values, condition_fn):
    intervals = []
    start = None
    for i in range(len(values)):
        if values[i] != 0:  # Skip positions with zero (non-extrema)
            if start is None:
                start = i
            if i == len(values) - 1 or not condition_fn(values[start:i+1]):
                end = i if condition_fn(values[start:i+1]) else i - 1
                intervals.append((start, end))
                start = None
    return intervals

# Condition functions for stability intervals
def max_stability_condition(segment):
    return all(segment[0] >= x >= segment[-1] for x in segment)

def min_stability_condition(segment):
    return all(segment[0] <= x <= segment[-1] for x in segment)

# Intersection of intervals
def find_intersection(intervals1, intervals2):
    intersections = []
    for start1, end1 in intervals1:
        for start2, end2 in intervals2:
            if start1 <= end2 and start2 <= end1:  # Overlapping condition
                intersection_start = max(start1, start2)
                intersection_end = min(end1, end2)
                # Ensure that the intersection has more than 10 consecutive values
                if intersection_end - intersection_start + 1 > 10:
                    intersections.append((intersection_start, intersection_end))
    return intersections

# Main computation
local_maxima = find_local_maxima(random_values)
local_minima = find_local_minima(random_values)

max_stability_intervals = find_stability_intervals(local_maxima, max_stability_condition)
min_stability_intervals = find_stability_intervals(local_minima, min_stability_condition)

intersection_intervals = find_intersection(max_stability_intervals, min_stability_intervals)

# Results
print("Random Values:", random_values)
print("\nLocal Maxima:", local_maxima)
print("\nLocal Minima:", local_minima)
print("\nLocal Maxima Stability Intervals:", max_stability_intervals)
print("\nLocal Minima Stability Intervals:", min_stability_intervals)
print("\nIntersection of Stability Intervals (more than 10 consecutive values):", intersection_intervals)
