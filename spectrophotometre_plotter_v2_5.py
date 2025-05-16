import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

# Fichier et format
nom = "Phosphate Eu.csv"
separateur = ","
decimale = "."

# Bornes de tronquage (en nm)
lambda_min = 310
lambda_max = 6700

# Lissage de la dérivée
lisser_derivative = True      # Mettre False pour désactiver
coef_lissage = 11             # Doit être impair et < len(x)

# Chargement
df = pd.read_csv(nom, sep=separateur, skiprows=2, header=None, decimal=decimale)
df[0] = pd.to_numeric(df[0], errors="coerce")
df[1] = pd.to_numeric(df[1], errors="coerce")
df.dropna(subset=[0, 1], inplace=True)

# Tronquage
df = df[(df[0] >= lambda_min) & (df[0] <= lambda_max)]

# Extraction
x = df[0]
y = df[1]

# Dérivée : lissée ou non
if lisser_derivative and len(x) >= coef_lissage:
    dy_dx = savgol_filter(y, window_length=coef_lissage, polyorder=2, deriv=1, delta=np.mean(np.diff(x)))
else:
    dy_dx = np.gradient(y, x)

# Détection des extrema : changement de signe de la dérivée
zero_crossings = np.where(np.diff(np.sign(dy_dx)))[0]
extrema_x = x.iloc[zero_crossings + 1]  # +1 car diff réduit la taille de 1
extrema_y = y.iloc[zero_crossings + 1]

# Tracé
plt.figure(figsize=(10, 6))

plt.subplot(2, 1, 1)
plt.plot(x, y, label="Original", color='blue')
plt.scatter(extrema_x, extrema_y, color='black', marker='x', label='Extrema')

# Affichage d’un seul label par tranche de 50 nm
labeled_bins = set()
for x_val, y_val in zip(extrema_x, extrema_y):
    bin_key = int(x_val // 80)
    if bin_key not in labeled_bins:
        plt.annotate(f"{x_val:.0f} nm", xy=(x_val, y_val),
                     xytext=(0, 10), textcoords="offset points",
                     ha='center', fontsize=8, color='black')
        labeled_bins.add(bin_key)

plt.xlabel("Longueur d’onde (nm)")
plt.ylabel("Transmission")
plt.title("Spectre UV-Visible - " + nom)
plt.legend()
plt.grid(True)

plt.subplot(2, 1, 2)
plt.plot(x, dy_dx, color='red', label="d(Transmission)/dλ")
plt.axhline(0, color='gray', linestyle='--', linewidth=0.8)
plt.scatter(extrema_x, dy_dx[zero_crossings + 1], color='black', marker='x')
plt.xlabel("Longueur d’onde (nm)")
plt.ylabel("d(Transmission)/d(λ)")
plt.title("Dérivée du spectre")
plt.grid(True)

plt.tight_layout()
plt.show()

# Affichage texte des longueurs d’onde des extrema
print("Longueurs d'onde des extrema (∂T/∂λ = 0) :")
for lx, ly in zip(extrema_x, extrema_y):
    print(f"λ = {lx:.2f} nm → T = {ly:.3f}")
