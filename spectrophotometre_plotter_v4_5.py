import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

# Paramètres de base
noms_fichiers = [
    #"PEu.csv",
    #"P-Eu.csv",
    #"Te-Eu.csv",
    
    #"Tellurite.csv",
    #"Phosphate Cr.csv",
    #"Phosphate Eu.csv",
    
    #"Tellurite_abs.csv",
    
    "Phosphate IR.csv",
    "Tellurite IR.csv"
]

# Limites de longueur d'onde à afficher (en nm)
lambda_min = 280
lambda_max = 6900

# Fonction de détection automatique du séparateur et du décimal
def detect_format(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        for _ in range(2):  # sauter les deux premières lignes
            next(f)
        line = f.readline()
        if ";" in line:
            return ";", ","
        elif "," in line and "." in line:
            return ",", "."
        else:
            raise ValueError(f"Format non reconnu dans le fichier : {file_path}")

# Liste pour stocker les données
donnees = []
x_min_global = float('inf')
x_max_global = float('-inf')

# Chargement des fichiers valides
for nom in noms_fichiers:
    if not os.path.isfile(nom):
        print(f"Fichier non trouvé : {nom}")
        continue
    try:
        separateur, decimale = detect_format(nom)
        df = pd.read_csv(nom, sep=separateur, skiprows=2, header=None, decimal=decimale)
        df[0] = pd.to_numeric(df[0], errors="coerce") / 1000  # conversion nm -> µm
        df[1] = pd.to_numeric(df[1], errors="coerce")
        df.dropna(subset=[0, 1], inplace=True)

        # Tronquage selon lambda_min et lambda_max (convertis en µm)
        df = df[(df[0] >= lambda_min / 1000) & (df[0] <= lambda_max / 1000)]

        donnees.append((df[0], df[1], nom))
        x_min_global = min(x_min_global, df[0].min())
        x_max_global = max(x_max_global, df[0].max())
    except Exception as e:
        print(f"Erreur lors du chargement de {nom} : {e}")

# Création de la figure avec deux sous-graphes
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [4, 0.3]})

# Tracé des spectres
for x, y, nom in donnees:
    ax1.plot(x, y, label=nom)

ax1.set_xlim(x_min_global, x_max_global)
#ax1.set_xticks(np.arange(x_min_global + 0.020, x_max_global + 0.001, 0.025))
ax1.set_xticks(np.arange(x_min_global + 0.199, x_max_global + 0.001, 0.5))
ax1.set_xlabel("Longueur d’onde (μm)")
ax1.set_ylabel("Absorption (%)")
#ax1.set_title("Spectres UV-Visible superposés")
ax1.set_title("Spectres IR superposés")
ax1.legend()
ax1.grid(True)

# Création du spectre de couleurs (conservé en nm)
def wavelength_to_rgb(wavelength):
    if 380 <= wavelength <= 440:
        R = -(wavelength - 440) / (440 - 380)
        G = 0.0
        B = 1.0
    elif 440 < wavelength <= 490:
        R = 0.0
        G = (wavelength - 440) / (490 - 440)
        B = 1.0
    elif 490 < wavelength <= 510:
        R = 0.0
        G = 1.0
        B = -(wavelength - 510) / (510 - 490)
    elif 510 < wavelength <= 580:
        R = (wavelength - 510) / (580 - 510)
        G = 1.0
        B = 0.0
    elif 580 < wavelength <= 645:
        R = 1.0
        G = -(wavelength - 645) / (645 - 580)
        B = 0.0
    elif 645 < wavelength <= 780:
        R = 1.0
        G = 0.0
        B = 0.0
    else:
        R = G = B = 0.0
    return (R, G, B)

wavelengths_nm = np.linspace(x_min_global * 1000, x_max_global * 1000, 400)
rgb_colors = [wavelength_to_rgb(wl) for wl in wavelengths_nm]

# Affichage de la bande de couleur
ax2.imshow([rgb_colors], extent=[x_min_global, x_max_global, 0, 1], aspect='auto')
ax2.set_xlim(x_min_global, x_max_global)
ax2.set_yticks([])
ax2.set_xlabel("Longueur d'onde (μm)")
ax2.set_title("Spectre")

plt.tight_layout()
plt.show()
