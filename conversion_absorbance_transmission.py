import pandas as pd
import numpy as np

# Nom du fichier
nom_fichier = "tellurite.csv"

# Lecture avec bon séparateur et décimale
df = pd.read_csv(nom_fichier, skiprows=2, header=None, sep=",", decimal=".")

# Suppression des lignes non numériques
df = df[pd.to_numeric(df[0], errors='coerce').notnull()]
df = df[pd.to_numeric(df[1], errors='coerce').notnull()]

# Conversion en float
longueur_donde = df[0].astype(float)
transmission = df[1].astype(float)

# Calcul absorbance
transmission_clipped = transmission.clip(lower=0.1)
absorbance = -np.log10(transmission_clipped / 100)

# Création et sauvegarde du nouveau CSV
df_abs = pd.DataFrame({
    "Longueur d'onde (nm)": longueur_donde,
    "Absorbance": absorbance
})
df_abs.to_csv("tellurite_abs.csv", index=False)

print("Fichier 'tellurite_abs.csv' généré avec succès.")
