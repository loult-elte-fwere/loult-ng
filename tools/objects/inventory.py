from typing import List

from collections import defaultdict

from .base import LoultObject


class UserInventory:

    def __init__(self):
        self.objects = [] # type: List[LoultObject]

    def get_listing(self):
        sorted_inventory = defaultdict(int)
        for obj in self.objects:
            sorted_inventory[type(obj)] += 1

        return ", ".join("%s(%i)" % (obj_type.NAME, count) for obj_type, count in sorted_inventory.items())

    def remove(self, obj: LoultObject):
        self.objects.remove(obj)

    def add(self, obj: LoultObject):
        self.objects.append(obj)