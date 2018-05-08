# Un système d'antiflood pour le lou

Ou comment se défendre des raids du 18-25 en s'amusant

## Vue d'ensemble des règles du système

Le but d'un système antiflood sur le lou serait de prévenir les attaques de flood massives des randoms qui se connectent depuis JVC. 
En général, ces attaquent ne posent pas trop de problème si les flooders sont en nombre restreints :il suffit de mute un random
qui se connecte de temps en temps et ça suffit. 

Cependant, quand le volume de pyjs devient trop important, il devient intéressant 
d'avoir un système qui oeuvre au bien être des loutiste de façon quasi-autonome.
Le système est en deux parties: 

1. Le détecteur de flood, qui va tagguer un utilisateur comme "flooder" s'il produit trop de message dans une fenêtre de temps 
donnée. Un utilisateur taggué comme flooder subit ce qu'on pourrait appeller un "shadowmute".
2. Le système de bannissement actif, qui permet au loutistes de prendre eux-même part à la défense du loult

## Le Détecteur de flood
La procédure de détection de flood est la suivante:

1. Si un utilisateur crée trop de messages dans une fenêtre de temps donnée (par exemple, il exècede une moyenne de 3 messages 
par secondes pendant 10 secondes), le détecteur l'avertit
2. S'il persiste à flooder pendant, par exemple, 10 secondes de plus, le détecteur le tag en tant que flooder
3. Le flooder peut alors encore flooder, mais il sera le seul à voir son message (qui, pour éviter toute charge système,
ne subit pas les effets éventuels appliqués à cet utilisateur). Il est ainsi convaincu de continuer à emmerder le monde, et en réalité 
il se pourrit tout seul

A noter que le cookie du flooder est alors taggué comme "flooder" dans une liste propre à l'ensemble du site (dans l'objet LoultState),
jusqu'a expiration de cet état (mettons, 30min par exemple). Ainsi, la déconnection/reconnection le n'aide en rien

## Système de bannissement actif

Quand le système antiflood a taggué un utilisateur comme "Flooder", une notification est envoyée aux autres loultistes en présence.
Ils sont alors invités à attaquer le flooder avec la commande `/attack nompokéflooder`, de la même façon qu'avec le système d'attaque 
usuel.

Chaque attaque portée au flooder va déclencher l'envoi d'un masse énorme du même message (par exemple, 100 fois), qui sera,
en toute logique, une phrase tirée d'un florilège des mêmes du lou. Si suffisament de loutistes déclenchent une attaque, le client
du flooder sera surchargé et le type devra déconnecter. **Lors de la déconnection du flooder, les loutistes sont notifiés 
de cette déco par un message leur indiquant qu'ils ont vaincu le flooder**.

Cette technique, en plus d'ête ludique, ne charge que peut le serveur: en effet, 10 messages du flooder envoyés à 10 clients (ce qui est fréquent)
nécessitent déjà 100 envois (et le serveur s'en sort très bien). Ainsi; 100 messages d'un coup sur un unique client n'est pas un poids
conséquent pour le serveur, mais plutot lourd pour le navigateur du flooder qui va devoir traiter un sacré paquets de messages d'un coup
(sans parler du lecteur audio qui devra mixer 100 tracks wav d'un coup).

## Todo

 * Modifier les users pour qu'ils aient une référence sur leurs clients connectés
 * Réparer le bug des attaques sur l'utilisateur banni