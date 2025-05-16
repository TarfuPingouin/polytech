import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paramètres 
nom_fichier = "Phosphate Eu.csv"  # à adapter pour chaque verre
longueur_echantillon_cm = 0.5  # 5 mm d'épaisseur en cm
seuil_alpha = 10  # ou 4 si on n'atteint pas 10
lambda_min = 300  # longueur d'onde minimale à conserver
lambda_max = 1200  # longueur d'onde maximale à conserver

# Lecture des données
df = pd.read_csv(nom_fichier, skiprows=2, header=None, sep=",", decimal=".")
df = df[pd.to_numeric(df[0], errors='coerce').notnull()]
df = df[pd.to_numeric(df[1], errors='coerce').notnull()]

# Conversion et tronquage
longueur_donde_nm = df[0].astype(float)
transmission_pct = df[1].astype(float)
mask_troncage = (longueur_donde_nm >= lambda_min) & (longueur_donde_nm <= lambda_max)
longueur_donde_nm = longueur_donde_nm[mask_troncage]
transmission_pct = transmission_pct[mask_troncage]

# Calcul du coefficient d'absorption alpha en cm^-1
t_pct_clipped = transmission_pct.clip(lower=0.1)
alpha = -np.log(t_pct_clipped / 100) / longueur_echantillon_cm

# Trouver la première longueur d'onde où alpha >= seuil
mask = alpha >= seuil_alpha
if mask.any():
    lambda_bandgap_nm = longueur_donde_nm[mask].iloc[0]
    energie_bandgap_eV = 1239.8 / lambda_bandgap_nm
else:
    lambda_bandgap_nm = None
    energie_bandgap_eV = None

# Affichage graphique
plt.figure(figsize=(10, 6))
plt.plot(longueur_donde_nm, alpha, label="Alpha (cm⁻¹)", color="blue")
plt.axhline(seuil_alpha, color='red', linestyle='--', label=f"Seuil = {seuil_alpha} cm⁻¹")

if lambda_bandgap_nm:
    plt.axvline(lambda_bandgap_nm, color='green', linestyle='--', label=f"Band gap à {lambda_bandgap_nm:.1f} nm")
    plt.text(lambda_bandgap_nm, seuil_alpha + 5, f"{lambda_bandgap_nm:.1f} nm\n{energie_bandgap_eV:.2f} eV",
             ha='left', va='bottom', color='green')

plt.xlabel("Longueur d'onde (nm)" + " " + nom_fichier)
plt.ylabel("Coefficient d'absorption α (cm⁻¹)")
plt.title("Spectre d'absorption")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# Résultat
if lambda_bandgap_nm:
    print(f"\nBand gap atteint à {lambda_bandgap_nm:.1f} nm (alpha = {seuil_alpha} cm^-1)")
    print(f"Energie correspondante : {energie_bandgap_eV:.2f} eV")
else:
    print("\nLe seuil alpha n'est pas atteint dans ce spectre.")
