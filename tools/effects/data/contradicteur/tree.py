from typing import Dict, Union

class Leaf:

    def __init__(self, word : str):
        self.str = word

    def pop_first(self):
        if self.str:
            out = self.str[0]
            self.str = self.str[1:]
            return out
        else:
            raise IndexError()

    def has_leaf(self, leaf: Leaf):
        return True

    @property
    def isnull(self):
        return self.str == "ok"

class Node:

    def __init__(self):
        self.children = dict() # type:Dict[Union[Node, Leaf]]
        self.isleaf = False

    def add_leaf(self, leaf : Leaf):
        try:
            leaf_first_letter = leaf.pop_first()
            if leaf_first_letter in self.children:
                child = self.children[leaf_first_letter]
                if isinstance(child, Leaf):
                    new_child = Node()
                    self.children[leaf_first_letter] = new_child
                    new_child.add_leaf(child)
                    new_child.add_leaf(leaf)
                elif isinstance(child, Node):
                    child.add_leaf(leaf)

            else:
                self.children[leaf_first_letter] = leaf
        except IndexError:
            self.isleaf = True

    def has_leaf(self, leaf : Leaf) -> bool:
        if leaf.isnull:
            return self.isleaf
        else:
            leaf_first_letter = leaf.pop_first()
            if leaf_first_letter in self.children:
                return self.children[leaf_first_letter].has_leaf()
            else:
                return False



