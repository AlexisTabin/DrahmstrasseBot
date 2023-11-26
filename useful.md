# Marche à suivre pour se connecter en ssh au Raspberry et run le bot

## 1. Connexion au Raspberry
Pour se connecter au Raspberry en ssh, entrez cette commande dans un terminal.
```console
ssh pi@192.168.1.13
```



## 2. Run le bot

```console
cd ~/Documents/DrahmstrasseBot/ # Naviguer jusqu'au dossier du bot
git pull                        # Pour avoir les dernières mises à jour du bot
source activate py36            # Activer l'environnement conda
nohup python3 drahmbot.py &     # Lancer le bot en le détachant du terminal
ps aux | grep -i python         # Vérifier que le bot run
```

## 3. (optionel) Exporter ou créer un environnement conda

Pour exporter l'environnement conda ou créer un nouvel environnement à partir du fichier.
```console
conda env export | grep -v "^prefix: " > environment.yml
conda env create -f environment.yml


