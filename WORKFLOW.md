# Loult-ng : *Workflow* Git et bonnes pratiques

## Introduction

Ce document s'adresse à tout contributeur désireux de participer au développement du projet. Il décrit, sans s'imposer comme un standard entièrement normé, un *workflow* général à suivre pour le développement et les bonnes pratiques liées au versioning d'un projet comme le Loult. Le *workflow* en question est directement repris d'un modèle populaire décrit dans un billet de Vincent Driessen, *A successful Git branching model*. Il s'agit d'une méthode suffisamment souple pour être adaptée à la taille et au cycle de vie d'un programme comme celui-ci. Suivre un plan semblable assure au minimum de délivrer en production du code sans bugs majeurs et facilite grandement la coordination entre les différents collaborateurs, que leur participation soit ponctuelles ou plus régulières. 

Le projet est déjà vieux de plusieurs années et a connu un développement toujours un peu «organique», jalonné de collaborations parfois brèves ou difficiles. Débiter des idioties par l'intermédiaire d'un moteur de synthèse vocale et d'un créole unique demande beaucoup d'investissement. Malgré le ridicule de la finalité, la somme du code produit depuis la conception mérite qu'on standardise un minimum la façon de faire grandir le projet.

## Fonctionnement général

Le modèle de développement adopté fait grand usage du système de __branches__ de Git. Il s'articule autour de deux branches majeures et permanentes, la __master__, le code stable destiné à être mis en *production*, et la __dev__, qui reflète l'état le plus à jour du projet et récupère les derniers changements introduit pendant le développement. 

Des branches auxilliaires et temporaires sont utilisées en parallèle de ces deux branches permanentes : Les branches de __features__ introduisent de nouveaux fonctionnalités et comportements dans l'applications, celles de __hotfix__ pour la correction des bugs critiques affectent la production autant que la branche de dev, et celles de __releases__, qui marquent une version potentiellement stable et déployable en production de l'application. Elle est associée de préférence avec une description des nouvelles fonctionnalités et des bugs corrigés. 

Dans le cas du projet (Loult), le rôle des branches de versions est rempli par l'utilisation des *tags* de Git, qui marquent dans l'historique les versions stables introduisant des changements clefs.

## Détails de la stratégie de fusion des branches

### Master pour la production
La branche __master__ reflète le code déployé en production. Elle est permanente sur le dépôt *origin*. L'intérêt principal de suivre ce *workflow* est de faire en sorte que le code de la branche master soit toujours prêt à tourner en production : Stable, et sans bugs majeurs. Aussi, il faut éviter au maximum de pousser des changements vers cette branche. Hormis les bugs *critiques* incapacitant l'utilisation du programme, tous les changements doivent être introduit *au minimum* sur la branche de développement. Les seules fusion d'une branche vers la master devraient être celle de nouvelles versions solidement testées.

### Dev pour le développement
La branche __dev__ est la banche principale de développement. Elle est également permanente. C'est sur cette branche qu'on trouve les derniers changements introduits durant le développement en préparation d'une version destinée à la production : Ajout de fonctionnalités, évolution ou corrections de bugs. C'est sur cette branche que sont d'abord poussés tous les changements. Lorsque la branche atteint un état stable et propre à la rendre déployable, on inscrit le *changelog* dans dans la description du commit cible, on marque dans l'historique le numéro de version, et la branche est prête à être fusionnée avec la master via un __merge__. La seule interaction avec la master, optimalement, devrait être celle-ci. Tout le reste passe par la dev.

`Le développement du projet pourrait à ce stade se suffire de ces deux branches et de cette très simple méthodologie.`

Il serait en effet possible de se contenter de cet ensemble de règles, mais l'usage de branches temporaires est, dans l'état actuel du projet, presque nécessaire pour l'intégration de nouvelles fonctionnalités et d'évolutions qui rendraient la vie difficile aux collaborateurs qui travaillent eux aussi sur la dev, mais sur des fonctionnalités différentes : Citons par exemple une modification en profondeur de la gestion des messages cotés serveur, l'utilisation d'un nouveau framework pour le client, ou la refonte du système de modération.

L'historique du projet montre l'utilisation régulière de branches temporaires très semblables à celles décrites dans ce document. Ce qui suit n'est qu'une description un peu plus formelle de ce qui se pratiquait déjà au Jurassique Loultien. Les nouveaux contributeurs auront une idées plus clairs du fonctionnement général, et les habitués ne devraient pas être bouleversés dans leurs habitudes. 

### Branches de *features* pour les fonctionnalités et corrections de bugs

Les branches de *features*, comme leur nom l'indique, concernent le développement des nouvelles fonctionnalités du projet et l'évolution de celles déjà existantes. Elles sont prioritairement __basées sur la branche dev__ et doivent être __fusionnées sur la dev__. Il n'est pas nécessaire de pousser ces branches sur le dépôt *origin* (le Github). Elles sont temporaires et peuvent être supprimées une fois la fonctionnalité développée et introduite en dev, ou malheureusement abandonnée. La convention de nommage n'est pas vraiment normée, mais il est préférable de nommer ces branches clairement : Pour soi-même, mais surtout pour les autres si jamais les branches sont poussées sur le dépôt distant.

Par extension, on inclut ici dans cette catégorie toute branche qui se charge en priorité de corriger un bug ou de résoudre une inconvenance mineure, de préférence rapportée et décrite dans une *issue*. Sauf pour les problèmes simples qui se résolvent en un commit directement sur la dev, préférez la création d'une branche associée à un bug ou une issue. Cela ne coûte rien et vous pourrez supprimer la branche une fois le bug corrigé... Ou la recréer s'il revient, ce qu'une stratégie de versioning comme celle-ci tente de faire disparaître autant que possible.

La frontières entre une fonctionnalité et une correction de bugs est parfois floue, mais la règle générale est la suivante :

`Faites des branches basées sur dev. Fusionnez les avec dev une fois le travail terminé. Supprimez les une fois qu'il est inutile de les garder.`

Exemple : `git checkout -b outils-moderation-sadique dev`

### Branches de *hotfix* ou de corrections de bugs

La deuxième catégorie de branches temporaires concerne celle qui corrigent les bugs critiques en production : Les branches __hotfix__. Ces branches sont __basées sur la master__ et sont fusionnées __sur la master et sur la dev__. Seuls les bugs très critiques, incapacitant l'utilisation du programme, sont concernés. Le reste des bugs se merge dans dev comme décrit précédemment. La convention de nommage à respecter est de préfixer le nom de la branche par *hotfix-*. Les branches hotfix étant déployées sur la master, elles affectent le numéro de version, il est ainsi important de prendre compte cela avant de faire un commit ou de fusionner.

## Numéro de versions

Les versions sont décrites via les tags Github plutôt qu'une autre famille de branche, par simplicité. Une version est un point repère dans la branche de développement qui marque un moment ou celle ci peut passer en production : Elle est stable et sans bugs critiques connus, corrige d'anciens bugs et apportent de nouvelles fonctionnalités. Le numéro de version est construit sur le modèle suivant :

`version_majeure.version_mineure.hotfix`

Les __versions majeures__ incluent des changements qui cassent la compatibilité avec la version majeure précédentes. Ça n'est pas le cas des __versions mineures__ ni des __hotfix__. Le numéro de hotfix est optionnel, puisque ces branches sont créées et fusionnées seulement en cas d'incident majeur.

## Issue et Pull Request

Les __issues__ servent à : 
+ Déclarer des bugs
+ Proposer de nouvelles fonctionnalités
+ Discuter de l'évolution technique du projet

Les issues ne sont *pas* faites pour la gestion propre à la vie du site et aux conflits entre les utilisateurs finaux. C'est la *teknès*, on est là pas la bricole, pas pour le drama.

Les __pull request__ permettent aux contributeurs ponctuels de proposer des fonctionnalités sans avoir un accès en écriture au dépôt distant. Elles peuvent également (et devraient) être utilisées par les réguliers dans le cas de fonctionnalités susceptibles de ne pas faire l'unanimité : Le développement est communautaire, mais le projet depuis le début est en définitif gérer par celui qui héberge le site, et paye la bande passante pour ces instants d'échanges d'une spiritualité sans équivoque. 

L'administrateur et gestionnaire du projet peut refuser de merger votre code pour différentes raisons, aussi n'hésitez pas à clarifier votre demande et discuter avec *avant* de passer du temps sur le code. Il est aussi frustrant pour l'administrateur de tester et refuser votre contribution que pour vous qui avez perdu du temps sur quelque chose que vous pensiez acceptable.

`Si vous doutez de la légitimité de votre apport ou n'êtes pas encore très à l'aise avec Git, faites une branche, et ouvrez une pull request.`

## Bonne pratique Git et Github pour le projet

+ Fusionnez avec l'option `--no-ff` pour «aplatir l'historique» de commit et voir tous les commits de la branche temporaire apparaître dans la dev.

+ Tirer (git pull) les changements avec l'option `--rebase` pour éviter les commits de merge qui vont polluer l'historique à chaque fois.

+ Soignez autan que possible les titres de vos commits, et si possible ajouter une description plus complète des changements dans son corps quand c'est judicieux.

+ Récupérer les changements distants récents avant de travailler sur une branche locale propre.

+ Décrivez bien les issues, n'hésitez pas à utiliser les tags pour rendre identifiable son objet : Bug, question, amélioration, etc.

+ Mentionnez le numéro de l'issue ou de la pull request sur laquelle vous travaillez dans vos titre de commits ou de branches en utilisant la syntaxe #numero : `added a new anti-flood option in menu (issue #34)`. Une mention du commit ou de la branche apparaîtra automatiquement dans l'issue portant le numéro. 

## Trop Long; Pas Lu.

+ On ne touche __jamais__ à la branche __master__ *sauf* pour 1) Les mettre une nouvelles *versions* 2) corriger des bugs critiques (*hotfix*)
+ Le développement se fait sur __dev__, directement si le changement est mineur, dans le doute et de préférence via des branches temporaires qu'on fusionne une fois le travail terminé.
+ Si vous avez du mal avec Git ou doutez que vos changements soient acceptés, ouvrez une pull request, et implémentez __après__ la confirmation de celui qui gère le projet. Les bénéfices sont mutuels. 

## Conclusion

Ce document est amené à évoluer régulièrement, pour être corrigé, rendu plus clair, ou simplement s'adapter à la pratique du développement. S'efforcer de suivre ce qui y est indiqué ne vous garantira pas l'argent, le bonheur et les bonnes nuits de sommeil. Pour celui qui maîtrise encore mal Git, ces étapes peuvent sembler inutiles, incompréhensibles ou simplement difficile à mettre en oeuvre. Il s'agit pourtant d'une méthodologie simple qui a fait ses preuves, et quelqu'un qui maîtrise les commandes basiques de Git devrait vite trouver ses repères. 

Ce genre de petites règles et de procédures rendent le développement encore plus ludique, et assure la satisfaction du besoin fondamental qui nous motive (ou nous a motivé) à contribuer : Un site stable et riche pour s'insulter avec des voix robotiques rigolotes.


## Références

+ [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/)
+ [Comparing Workflows](https://www.atlassian.com/git/tutorials/comparing-workflows)
+ [Git Branching - Basic Branching and Merging](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging)
+ [Automate Python workflow using pre-commits: black and flake8](https://ljvmiranda921.github.io/notebook/2018/06/21/precommits-using-black-and-flake8/)

Suggestion : Passez par l'issue #2 pour signaler les coquilles
