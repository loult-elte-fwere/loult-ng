Un chat de pokémons avec synthèse vocale. D'après une œuvre de *@DrEmixam*.

La partie client est en HTML/CSS/JS statique et la partie serveur en Python.

# Installation

* Installez nginx, python3-venv, le synthétiseur vocal mbrola,
espeak et sox:
```
sudo apt install git nginx mbrola espeak sox python3 python3-venv python3-dev python3-pip portaudio19-dev build-essential
sudo ./install/voices_install.py
```

Il faut aussi installer les voix-mbrola, via le script-outils de voxpopuli.
Pour installer toutes les voix supportées par le Loult via ce script, lancez:

```bash
sudo python3 -m vopopuli.voice_install fr us es de
```

* Clonez le lou sur votre propre machine :
```bash
git clone https://github.com/4577/loult-ng.git
cd loult-ng
```
* Créez un petit venv :
```bash
python3 -m venv venv
source venv/bin/activate
```
* Installez d'abord `numpy` et `wheel` avec `pip install numpy wheel`
* installez le reste des dépendances : `pip install -r requirements.txt`
* Créez un fichier `salt.py` contenant `SALT = '<valeur arbitraire>'`
* Configurez nginx en vous servant de `loult.conf` (notamment adaptez le chemin de `$static`)
```bash
cp loult.conf /etc/nginx/sites-available/
ln -s /etc/nginx/{sites-available,sites-enabled}/loult.conf
systemctl reload nginx
```
* Lancez `python3 poke.py`

# Usage

* Les options de configuration disponibles sont décrites dans `conf.py`.
* Tapez `/aide` dans la zone de texte du chat pour avoir accès à la liste des commandes disponibles.
* Un système d'antiflood automatique est intégré ; il exclut un utilisateur sur la base de son cookie
s'il poste trop vite par deux fois.

## Combat

Les utilisateurs peuvent s'attaquer les uns les autres en lançant la commande `/attack Taupiqueur`.
S'il y a plusieurs pokémons à ce nom dans le chat, on peut rajouter son numéro dans la liste,
comme `/attack Taupiqueur 3`, ce qui attaquera le 3ème Taupiqueur dans la liste.

Il y a un temps minimum entre chaque nouvelle attaque par un utilisateur. Cela peut être configuré.

## Bans manuels

Le système de ban utilise le pare-feu de Linux pour éviter de faire consommer
des ressources au serveur python. Il faut cependant au préalable configurer
ce pare-feu en y ajoutant quelques règles. Vous pouvez vous inspirer ou utiliser
directement `nftables.conf.sample`. À noter qu'aucune interface ni outil n'est fourni
pour placer ces bans manuels, vous devez lire `tools/ban.py` pour un implémenter un.

Supposons que la table `filter` de type `inet` contienne une chaîne nommée
`input` pour le hook `input` et une chaîne `output` pour le hook `output`.
Les règles à rajouter sont alors :

	nft add set inet input ban "{type ipv4_addr; flags timeout;}"
	nft add set inet input slowban "{type ipv4_addr; flags timeout;}"
	nft add rule inet filter input ip saddr @ban ct state new,established drop
	nft add rule inet filter input ip saddr @slowban ct state new,established flow table slowban_in { ip saddr limit rate over 250 bytes/second } drop
	nft add rule inet filter output ip daddr @slowban ct state new,established flow table slowban_out { ip daddr limit rate over 10 kbytes/second } drop


Voici un moyen de faire marcher ce système entre chaque redémarrage du serveur :

* installez `nftables` et assurez-vous que la commande `nft` puisse être
  lancée par l'utilisateur lançant loult-ng sans entrer de mot de passe
* copiez `nftables.sample.conf` sur `/etc/nftables.conf`
* lancez `systemctl enable nftables` puis `systemctl restart nftables`

# Développement tiers

## API

Toutes les communications se font par websocket.
Son point d'entrée est `wss://<nom de domaine>/socket/<room>`
(ou `ws://...` si vous n'utilisez pas le chiffrement).

Les clients ne peuvent envoyer que des messages JSON. Ils reçoivent des messages JSON
et des messages binaires correspondant aux sons. Un son correspondant à un message JSON
est envoyé juste après le message JSON ; il n'y a pas de marqueur associant un son à
un utilisateur.

Les messages envoyés par le client ont le format suivant : `{"type": <type>, "msg": <string>}`.
`<type>` peut être `"msg"` pour un message normal, `"me"` pour les actions à la IRC,
et `"bot"` pour que les bots puissent être plus discrets. Ce dernier type est accessible
seulement de manière programmatique, est rendu comme un message en italiques et de la couleur
associée au cookie du bot, sans synthèse vocale. Le type de message `"msg"` peut avoir
un paramètre supplémentaire, `"lang"`, avec pour valeur un code de deux lettres parmis
les langues disponibles : fr, en, es, de.

Outre les moyens de communication textuelle, il est possible d'envoyer des commandes
pour effectuer d'autres actions. Pour le moment, la seule autre action disponible est
l'attaque, avec le format suivant :
`{"type": "attack", "target": <nom du pokémon>, "order": <position dans la liste des utilisateurs (nombre entier)>}`.

## Fermeture impromptue du websocket

L'application définit des codes d'erreurs spéciaux lors de la fermeture
immédiate par le serveur d'un websocket :

| code | signification             |
|------|---------------------------|
| 4000 | Erreur inattendue         |
| 4001 | JSON malformé             |
| 4002 | Données binaires refusées |
| 4003 | Type de commande inconnu  |
| 4004 | Banni pour flood          |

