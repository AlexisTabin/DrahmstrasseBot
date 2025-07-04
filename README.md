# DrahmstrasseBot - Le bot du Drame de la Rue de la Drahm 

# Marche à suivre pour se connecter en ssh au Raspberry et run le bot

## 1. Connexion au Raspberry
Pour se connecter au Raspberry en ssh, entrez cette commande dans un terminal.
```console
ssh pi@192.168.1.13
```

## 2. Environment:

le fichier 'environment.yml' contient toutes les librairies nécessaires au fonctionnement du bot!

un simple
```console
conda install -f environment.yml
 ```
suffit!


Petite astuce: le fichier examples.py est impeccable pour commencer rapidement avec le bot :)


## 3. Run le bot

```console
cd ~/Documents/DrahmstrasseBot/ # Naviguer jusqu'au dossier du bot
git pull                        # Pour avoir les dernières mises à jour du bot
source activate py36            # Activer l'environnement conda requis
nohup python3 bot_main.py &     # Lancer le bot en le détachant du terminal
ps aux | grep -i python         # Vérifier que le bot run
```
Pour arrêter le bot:

```console
kill <PID>                      # Pour arrêter le bot
```

## 4. (optionel) Lancer le bot automatiquement au démarrage du Raspberry

Pour lancer le bot automatiquement au démarrage du Raspberry, il faut ajouter une ligne dans le fichier crontab.

```console
  crontab -e
```

et ajouter la ligne suivante à la fin du fichier.

```console
@reboot /usr/bin/sleep 60;  ~/Documents/DrahmstrasseBot/run-on-start-pi.sh > ~/Documents/DrahmstrasseBot/bot-pi.log 2>&1
```
Avant cela, ne pas oublier de chmod+x le script qu'on veut lancer

La commande `@reboot` permet de lancer la/les commande/s suivante/s au démarrage du Raspberry. Pour plus d'informations sur le fichier crontab, voir [ici](https://tecadmin.net/crontab-in-linux-with-20-examples-of-cron-schedule/).

La commande `sleep 60` permet d'attendre 60 secondes avant de lancer le bot. Cela permet de laisser le temps au Raspberry de se connecter au réseau wifi avant de lancer le bot.

La commande `> ~/Documents/DrahmstrasseBot/bot-pi.log 2>&1` permet de rediriger la sortie standard et la sortie d'erreur vers le fichier `bot-pi.log`. Cela permet de garder une trace des erreurs du bot. Plus précisément, `2>&1` permet de rediriger la sortie d'erreur vers la sortie standard. Pour rediriger toutes les sorties vers un fichier, il faut utiliser `&>`. Pour plus d'informations sur la redirection des sorties, voir [ici](https://www.tldp.org/LDP/abs/html/io-redirection.html).


