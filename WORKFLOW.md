# Loult-ng : *Workflow* Git et bonnes pratiques

## Introduction

Ce document s'adresse à tout contributeur désireux de participer au développement du projet. Il décrit, sans s'imposer comme un standard entièrement normé, un *workflow* général à suivre pour le développement et les bonnes pratiques liées au versionnage d'un projet. Le *workflow* en question est directement repris d'un modèle populaire (voir références) suffisamment souple pour être adapté à la taille et au cycle de vie d'un programme comme celui-ci. Suivre un plan comme celui-ci assure ...

## Fonctionnement général

Le modèle de développement adopté fait grand usage du système de __branches__ de Git. Il s'articule autour de deux branches majeures et permanentes, la __master__, le code stable destiné à être mis en *production*, et la __dev__, qui reflète l'état le plus à jour du projet et récupère les derniers changements introduit pendant le développement. Des branches auxilliaires et temporaires sont utilisées en parallèle de ces deux branches permanentes : Les branches de __features__ introduisant de nouveaux fonctionnalités et comportements dans l'applications, celles de __hotfixes__ pour la correction des bugs affectant la production, et celles de __releases__, qui marquent une version potentiellement stable et déployable en production de l'application. Elle est associée de préférence avec une descriptions des nouvelles fonctionnalités et des bugs corrigés. Dans le cas du projet (Loult), le rôle de la dernière branche est rempli par l'utilisation des tags de Git, qui marquent dans l'historique les versions stables introduisants des changements clefs.

## Détails de la stratégie de fusion des branches

### Master

### Dev

### Branches de *features*

### Branches de *hotfixes*

## Issue et Pull Request

## Bonne pratique Git pour le projet

## Références

+ [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/)
+ [Comparing Workflows](https://www.atlassian.com/git/tutorials/comparing-workflows)
+ [Git Branching - Basic Branching and Merging](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging)
+ [Automate Python workflow using pre-commits: black and flake8](https://ljvmiranda921.github.io/notebook/2018/06/21/precommits-using-black-and-flake8/)
