from os import path
import os
from tools.effects.tree import Leaf, Node
import pickle

###### WARNING : has to be copied and launched from the root of the project in order for picking to work
VERBS_FILEPATH =path.join("tools/effects/data/contradicteur", "liste_verbes.txt")
VERBS_TREE_FILEPATH =path.join("tools/effects/data/contradicteur", "verbs_tree.pckl")

tree = Node()

with open(VERBS_FILEPATH) as verbs_file:
    for verb in verbs_file:
        tree.add_leaf(Leaf(verb.strip()))

with open(VERBS_TREE_FILEPATH, "wb") as picklefile:
    pickle.dump(tree, picklefile)