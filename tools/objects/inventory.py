from typing import List

from collections import defaultdict

from .base import LoultObject


class UserInventory:

    def __init__(self):
        self.objects = [] # type: List[LoultObject]

    def get_listing(self):
        if self.objects:
            return ", ".join("%i : %s" % (obj_id, obj.name) for obj_id, obj in enumerate(self.objects))
        else:
            return "Queudal"

    def remove(self, obj: LoultObject):
        self.objects.remove(obj)

    def add(self, obj: LoultObject):
        if obj not in self.objects:
            self.objects.append(obj)

    def get_object_by_id(self, obj_id: int):
        try:
            return self.objects[obj_id]
        except IndexError:
            return None

    def search_by_class(self, obj_class):
        return [obj for obj in self.objects if isinstance(obj, obj_class)]

    def remove_by_class(self, obj_class):
        self.objects = [obj for obj in self.objects if not isinstance(obj, obj_class)]
