"""Function for power_supply.py
A PID heat ramp experiment has been fitted to a polynomium to be fed back into the power supply."""
import numpy as np

def poly_current(x, param):
    # Initialize
    if type(x) == int:
        y = 0.
        x = float(x)
    elif type(x) == float:
        y = 0.
    else:
        y = np.zeros(len(x))

    # Calculate
    for i in range(len(param)):
        y += param[i] * (x**i)

    return y

t_change = 160
param1 = [1.97412e+00, -5.610136e-02, 4.222524e-03, -7.447891e-05,
          5.8796189e-07, -2.1858488e-09, 3.11700276e-12]
param2 = [3.84551107e+00, 3.13766395e-03, 1.33381151e-05, -8.52580115e-08,
          1.96335874e-10, -2.15923940e-13, 9.58996158e-17]
