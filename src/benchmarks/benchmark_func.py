# src/benchmarks/benchmark_func.py
import numpy as np

def sphere(x):
    return np.sum(x**2)

def schwefel_2_22(x):
    return np.sum(np.abs(x)) + np.prod(np.abs(x))

def schwefel_2_21(x):
    dim = len(x)
    o = 0
    for i in range(dim):
        o += np.sum(x[0:i+1])**2
    return o

def max_absolute(x):
    return np.max(np.abs(x))

def quartic_noise(x):
    dim = len(x)
    return np.sum(np.arange(1, dim+1) * (x**4)) + np.random.rand()

def generalized_power(x):
    dim = len(x)
    o = 0
    for i in range(dim):
        o += np.abs(x[i])**(i + 1)
    return o

def weighted_sphere(x):
    dim = len(x)
    o = 0
    for i in range(dim):
        o += (i + 1) * x[i]**2
    return o

def composite_quadratic(x):
    D = len(x)
    return np.sum(x**2) + np.sum(0.5 * D * (x**2)) + np.sum(0.5 * D * (x**4))

def quartic_noise_simple(x):
    dim = len(x)
    return np.sum(0.5 * dim * x**4) + np.random.rand()

def rastrigin(x):
    dim = len(x)
    return np.sum(x**2 - 10 * np.cos(2 * np.pi * x)) + 10 * dim

def rastrigin_modified(x):
    dim = len(x)
    o = 0
    for i in range(dim):
        if np.abs(x[i]) < 0.5:
            o += x[i]**2 - 10 * np.cos(2 * np.pi * x[i]) + 10
        else:
            o += (np.round(2 * x[i]) / 2)**2 - 10 * np.cos(2 * np.pi * np.round(2 * x[i]) / 2) + 10
    return o

def ackley(x):
    dim = len(x)
    return -20 * np.exp(-0.2 * np.sqrt(np.sum(x**2) / dim)) - np.exp(np.sum(np.cos(2 * np.pi * x)) / dim) + 20 + np.exp(1)

def griewank(x):
    dim = len(x)
    return np.sum(x**2) / 4000 - np.prod(np.cos(x / np.sqrt(np.arange(1, dim+1)))) + 1

def schwefel_2_6_simple(x):
    return np.sum(np.abs(x * np.sin(x) + 0.1 * x))

def weierstrass(x):
    dim = len(x)
    a = 0.5
    b = 3
    kmax = 20
    c1 = a ** np.arange(0, kmax + 1)
    c2 = 2 * np.pi * b ** np.arange(0, kmax + 1)
    o = 0
    for i in range(dim):
        o += w(x[i], c1, c2)
    return o

def w(x, c1, c2):
    return np.sum(c1 * np.cos(c2 * (x + 0.5))) - len(c1) * np.sum(c1 * np.cos(c2 * 0.5))

def michalewicz_modified(x):
    return 1 - np.cos(2 * np.pi * np.sqrt(np.sum(x**2))) + 0.1 * np.sum(x**2)

def multimodal(x):
    dim = len(x)
    o = 0
    for i in range(dim - 1):
        o += x[i]**2 + 2 * x[i + 1]**2 - 0.3 * np.cos(2 * np.pi * x[i]) - 0.4 * np.cos(4 * np.pi * x[i + 1]) + 0.7
    return o

def branin(x):
    return (x[1] - (x[0]**2) * 5.1 / (4 * (np.pi**2)) + 5 / np.pi * x[0] - 6)**2 + 10 * (1 - 1 / (8 * np.pi)) * np.cos(x[0]) + 10
