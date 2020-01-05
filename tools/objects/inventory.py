from typing import List
import random

from .base import LoultObject, DestructibleObject


class UserInventory:

    def __init__(self):
        self.objects = [] # type: List[LoultObject]
        if random.randint(1, 15) == 1:
            from ..objects import get_random_object
            self.add(get_random_object())

    def get_listing(self):
        return [{"id": i,
                 "name": item.name,
                 "icon": item.icon} for i, item in enumerate(self.objects)]

    def remove(self, obj: LoultObject):
        self.objects.remove(obj)

    def add(self, obj: LoultObject):
        # at most 5 items of the same class
        if obj not in self.objects and len(self.search_by_class(type(obj))) < 5:
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

    def destroy_used_objects(self):
        self.objects = [obj for obj in self.objects if not obj.destroy]
