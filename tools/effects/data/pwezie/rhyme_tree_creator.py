#!/usr/bin/python3

import csv
import pickle
from os import path

from katalixia import RhymeTree

#### /!\ /!\ /!\ Doit être lancé depuis la racine du dépot /!\ /!\ /!\

WORDS_FILE = path.join(path.dirname(path.realpath(__file__)), "noms_communs.txt")
PICKLED_TREE = path.join(path.dirname(path.realpath(__file__)), "rhyme_tree.pckl")

if __name__ == "__main__":

    with open(WORDS_FILE) as words_csv:
        reader = csv.DictReader(words_csv, delimiter='\t')
        rhyme_tree = RhymeTree(rhyming_lang="fr")
        for row in reader:
            rhyme_tree.insert_rhyme(row["ortho"], {"genre" : row["genre"], "nombre" : row["nombre"]})

    with open(PICKLED_TREE, "wb") as pckl_file:
        pickle.dump(rhyme_tree, pckl_file)
