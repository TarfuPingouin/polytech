import pandas as pd
import matplotlib.pyplot as plt
import os

# Paramètres de base
noms_fichiers = [
    "PEu.csv",
    "phosphate.csv",
    "tellurite.csv",
    "Te-Eu.csv"
]

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

# Chargement des fichiers valides
for nom in noms_fichiers:
    if not os.path.isfile(nom):
        print(f"Fichier non trouvé : {nom}")
        continue
    try:
        separateur, decimale = detect_format(nom)
        df = pd.read_csv(nom, sep=separateur, skiprows=2, header=None, decimal=decimale)
        df[0] = pd.to_numeric(df[0], errors="coerce") / 10
        df[1] = pd.to_numeric(df[1], errors="coerce")
        df.dropna(subset=[0, 1], inplace=True)
        donnees.append((df[0], df[1], nom))
    except Exception as e:
        print(f"Erreur lors du chargement de {nom} : {e}")

# Tracé des spectres
plt.figure(figsize=(10, 6))

for x, y, nom in donnees:
    plt.plot(x, y, label=nom)

plt.xlabel("Longueur d’onde (nm)")
plt.ylabel("Absorbance")
plt.title("Spectres UV-Visible superposés")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
