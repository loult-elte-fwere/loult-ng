# Description du système d'attaque
**NB** : Pour l'instant, tout est implémenté sans le niveau et l'XP.
On verra déjà si ce système marche bien avec les loutiste avant de voir
si on peut complexifier.

## La phase de tirage des dés
Quand user1 attaque user2, chacun des utilisateurs renvoie 2 valeurs: 
le dé qu'il a tiré, et le bonus appliqué. Le bonus dépend de plusieurs
(et pourra dépendre de bien plus de) facteurs.

 * bonus d'attaque : bonus de temps d'inaction + bonus de niveau
 * bonus de défense : bonus de niveau

(on favorise quand même l'attaque, sinon personne prend jamais d'effets,
et c'est pas golri). Le bonus de temps d'inaction est calculé à partir
du temps resté sans attaquer (+1 / tranches de temps de repos),
le bonus de niveau est simplement la valeur du niveau.

A la fin de cette phrase, on a donc, avec les deux dés de valeur 
aléatoire tirée entre 0 et 100 inclus:

 * `BONUS_ATK`, `DICE_ATK`
 * `BONUS_DEF`, `DICE_DEF`

## Détermination de l'action suivant l'attaque
Le résultat de l'attaque est déterminée selon la suite conditionnelle
de cas suivant:

```
if DICE_ATK == 100:
    -> effet global
    -> +1 niveau pour l'attaquant
elif DICE_ATK == 0 or DICE_DEF == 100:
    -> fumble sur l'attaquant
    -> +1 niveau pour le défenseur is DICE_DEF == 100
elif DICE_DEF == 0:
    -> fumble sur le défenseur
elif DICE_ATK + BONUS_ATK < DICE_DEF + BONUS_DEF:
    if random(0,1) == 1:
        -> rebond de l'attaque sur un joueur aléatoire (sans jet de défense)
elif DICE_ATK + BONUS_ATK > DICE_DEF + BONUS_DEF:
    -> l'attaque passe normalement
    -> +1 pt d'XP pour l'attaquant
```
NB: ne pas confondre XP et niveau des joueurs 

## Description des effets spéciaux (fumble, global, rebond)

### Effet global
Tout le monde prend le même effet, lequel est choisi au hasard.
Typiquement c'est un effet un peu marrant qui fait pas trop de 
cacophonie, genre Tourette ou Crapwe

### Fumble
S'applique à un utilisateur. Il prend 4 effets aléatoires d'un coup, 
et c'est tout.

### Rebond
Un utilisateur aléatoire dans le salon se prend un effet au hasard 
(résultat classique d'une attaque mais sur un clampin random)

## À propos du niveau

Le niveau d'un utilisateur est une valeur qui ne sert à priori que dans
les attaques. Pour l'instant, il n'est même pas affiché explicitement. 
Quelques propriétés:

 * plafonné à 50
 * pour gagner des niveaux, il faut attaquer, ce qui permet, la plupart 
 du temps, de gagner de l'XP
 * il faut toujours plus d'XP pour grimper de niveau, mais la quantité
 d'XP pour faire le palier est en log du niveau (donc ça va)
 * quand on déco-reco, le niveau est reset (conséquence de l'archi,
 s'il y a mémoire, alors il faudra modifier l'archi de façon plus
 conséquente)