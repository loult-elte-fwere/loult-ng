class LoultObject:
    NAME = "stuff"

    @property
    def name(self):
        return self.NAME


class InertObject(LoultObject):
    """Object that doesn't do anything"""
    pass


class UsableObject(LoultObject):
    """Object that can be used"""
    pass


class ClonableObject(LoultObject):
    """Object that gets cloned when it's given to someone else"""
    pass