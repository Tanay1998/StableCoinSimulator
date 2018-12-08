import numpy as np
import matplotlib.pyplot as plt

def bin_data(data, bin_size):
    valid_length = (data.shape[0] // bin_size) * bin_size
    data = data[:valid_length]
    N = data.shape[0]
    binned = np.zeros(N // bin_size)
    for k in range(0, N, bin_size):
        binned[k // bin_size] = data[k : k + bin_size].mean()
    return binned

def plot_prices(market, price_func, bin_size=50, warmup=100, ideal_dev=0.1): 
    data = np.array(market.prices[price_func])[warmup:]
    binned = bin_data(data, bin_size)
    
    ideal = np.ones(binned.shape)
    plt.plot(ideal, 'r')
    plt.plot(ideal - ideal_dev, 'g--')
    plt.plot(ideal + ideal_dev, 'g--')
    plt.plot(binned, 'b')
#     plt.plot(market.prices['MAday'], 'y')
    plt.ylim(1.0 - ideal_dev * 5, 1.0 + ideal_dev * 5)