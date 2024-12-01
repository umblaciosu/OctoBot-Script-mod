import random

def generate_random_intervals_with_prices(size, start_range, end_range, max_duration, price_range):
    intervals_with_prices = []
    for _ in range(size):
        start = random.uniform(start_range, end_range - max_duration)
        end = start + random.uniform(1, max_duration)
        price_start = random.uniform(price_range[0], price_range[1])
        price_end = random.uniform(price_range[0], price_range[1])
        intervals_with_prices.append((start, end, price_start, price_end))
    return intervals_with_prices

random.seed(42)  # For reproducibility
maximum_list = generate_random_intervals_with_prices(
    50, 1682812800.0, 1684800000.0, 100000.0, (1900, 2000))
minimum_list = generate_random_intervals_with_prices(
    30, 1682812800.0, 1684800000.0, 100000.0, (1800, 1900))

print(maximum_list)

