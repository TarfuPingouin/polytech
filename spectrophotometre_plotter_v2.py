#Plotter pour fichiers CSV issu d'un spectrophotomètre UV-Visible.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

# Si il y à une grosse erreur, changer ; par , et , par .
nom = "tellurite.csv"
separateur = ";"
decimale = ","

# On saute les deux premières lignes
df = pd.read_csv(nom, sep=separateur, skiprows=2, header=None, decimal=decimale)

# Conversion forcée des colonnes
df[0] = pd.to_numeric(df[0], errors="coerce")
df[1] = pd.to_numeric(df[1], errors="coerce")
df.dropna(subset=[0, 1], inplace=True)

# Extraction des données
x = df[0]
y = df[1]

# Lissage et dérivée
window = 11 if len(x) > 11 else (len(x) // 2) * 2 + 1
y_smooth = savgol_filter(y, window_length=window, polyorder=3)
dy_dx = savgol_filter(y, window_length=window, polyorder=3, deriv=1, delta=np.mean(np.diff(x)))

# Tracé
plt.figure(figsize=(10, 6))

plt.subplot(2, 1, 1)
plt.plot(x, y, label="Original", alpha=0.5)
plt.plot(x, y_smooth, label="Lissé", color='blue')
plt.xlabel("Longueur d’onde (nm)")
plt.ylabel("Absorbance")
plt.title("Spectre UV-Visible (lissé)" + " " + nom)
plt.legend()
plt.grid(True)

plt.subplot(2, 1, 2)
plt.plot(x, dy_dx, color='red')
plt.xlabel("Longueur d’onde (nm)")
plt.ylabel("d(Absorbance)/d(λ)")
plt.title("Dérivée du spectre")
plt.grid(True)

plt.tight_layout()
plt.show()
