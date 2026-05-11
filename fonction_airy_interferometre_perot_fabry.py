import numpy as np
import matplotlib.pyplot as plt

I0 = 1
R = 0.95
d = 0.005
L = np.arange(499.95e-9, 500.05e-9, 1e-15)

I = I0 * ((1-R)**2)/(((1-R)**2)+4*R*np.sin((2*np.pi*d)/L)**2)

plt.plot(L*1e9, I)
plt.xlabel("Longueur d'onde (nm)")
plt.ylabel("I / I0")
plt.title("Transmission Fabry-Pérot")
plt.ticklabel_format(style='plain', axis='x', useOffset=False)
plt.grid()
plt.show()
