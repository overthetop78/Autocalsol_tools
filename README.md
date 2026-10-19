# Autocalsol Tools

Application Windows/Python pour extraire les courbes de charge depuis des
classeurs Excel ou des CSV, les convertir au format Autocalsol et rechercher
les doublons dans des fichiers tabulaires.

## Fonctions

- détection automatique des feuilles contenant une courbe de charge ;
- regroupement par numéro de compteur ;
- pas de sortie sélectionnable : 5, 10, 15, 30 ou 60 minutes (30 minutes par défaut) ;
- détection et consolidation des horodatages en double ;
- ajout des demi-heures manquantes par propagation de la dernière valeur ;
- production d'une année civile complète par fichier (17 520 ou 17 568 lignes) ;
- découpage automatique si plusieurs compteurs ou plusieurs années existent ;
- correction directe des CSV `date;heure;valeur` comme `add_missing_times` ;
- recherche complète de doublons internes ou externes dans des fichiers ou dossiers ;
- sélection métier des colonnes et règles de normalisation configurables ;
- tableau détaillé et exports de rapports CSV ou Excel ;
- mémorisation des derniers dossiers utilisés et des options, sans conserver
  les fichiers sources sélectionnés.

Les CSV Autocalsol sont écrits en UTF-8 avec BOM, séparateur `;`, avec les
colonnes `date`, `heure`, `valeur`.

## Organisation du code

```text
src/
├── core/       # modèles et lecture des courbes de charge
├── services/   # conversion Autocalsol et recherche de doublons
├── ui/         # application PySide6, composants et thème
└── utils/      # fonctions communes
tests/          # tests automatisés
main.py         # point d'entrée GUI et ligne de commande
```

Les préférences sont enregistrées dans
`%APPDATA%\AutocalsolTools\settings.ini`.

Comme dans le projet `duplicate-finder`, deux dossiers fixes sont créés à
côté de l'exécutable :

- `data/` pour les fichiers à analyser ;
- `output/` pour les rapports CSV et Excel du Duplicate Finder.

## Installation et lancement

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Mode ligne de commande :

```powershell
python main.py convert "rapport.xlsx" -o sortie
python main.py duplicates fichier1.csv fichier2.xlsx -o doublons.csv
```

## Exécutable Windows

```powershell
.\build.ps1
```

La distribution est créée dans `dist\AutocalsolTools\`. L'exécutable reste
léger et les bibliothèques Python/Qt sont rangées dans le sous-dossier `lib`.
Il faut conserver le dossier complet pour exécuter l'application.

## Build automatique GitHub

Le workflow `Build Windows` exécute les tests, construit l'application sur
Windows et produit `AutocalsolTools-Windows-x64.zip`.

- le workflow n'est pas lancé à chaque push sur `main` ;
- il peut être lancé manuellement avec **Run workflow**, le ZIP étant ensuite
  disponible dans les **Artifacts** ;
- après le push d'un tag `v*`, par exemple `v1.0.0`, le ZIP est publié dans
  l'onglet **Releases** du dépôt.

Exemple de publication d'une version :

```powershell
git tag v1.0.0
git push origin v1.0.0
```

