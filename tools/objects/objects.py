from datetime import datetime
import random
import re
from os import path, listdir
from time import time as timestamp

import yaml

from ..effects.effects import ExplicitTextEffect, GrandSpeechMasterEffect, StutterEffect, VocalDyslexia, \
    VowelExchangeEffect, FlowerEffect, CaptainHaddockEffect
from .base import userlist_dist, LoultObject, cooldown, destructible, targeted, inert, clonable
from ..tools import cached_loader

DATA_PATH = path.join(path.dirname(path.realpath(__file__)), "data")


@inert
@clonable
class DiseaseObject(LoultObject):
    DISEASES = ["syphilis", "diarrhée", "chaude-pisse", "gripe aviaire"]

    def __init__(self, patient_zero, disease=None):
        super().__init__()
        if disease is None:
            self.disease = random.choice(self.DISEASES)
        self.patient_zero = patient_zero

    @property
    def name(self):
        return "la %s de %s" % (self.disease, self.patient_zero)


@destructible
class Flower(LoultObject):
    ICON = "flower.gif"
    FLOWERS = ["rose", "lys blanc", "iris", "chrysanthème", "oeillet", "jonquille", "muguet",
               "tulipe", "orchidée"]

    def __init__(self):
        super().__init__()
        self.flower_name = random.choice(self.FLOWERS)
        self.remaining_uses = int(random.uniform(3, 6))

    @property
    def name(self):
        return self.flower_name

    def use(self, obj_params):
        if self.remaining_uses == 0:
            msg = "cette fleur est complètement fanée."
            self.self.notify_serv(msg=msg)
            self.should_be_destroyed = True
        else:
            name = self.user.poke_params.fullname
            msg = "{name} met une fleur dans ses cheveux, c twe miwmiw."
            self.channel.broadcast(type="notification", msg=msg.format(name=name))
            self.user.state.add_effect(FlowerEffect())
            self.remaining_uses -= 1


@destructible
class BaseballBat(LoultObject):
    ICON = "baseballbat.gif"
    FIGHTING_FX_DIR = path.join(DATA_PATH, "fighting/")
    BROKEN_BAT_FX = path.join(DATA_PATH, "broken_bat.mp3")

    def __init__(self, target_userid, target_username):
        super().__init__()
        self.target_name = target_username
        self.target_userid = target_userid
        self.remaining_hits = random.randint(5, 15)
        self.sounds = []
        for filename in listdir(self.FIGHTING_FX_DIR):
            realpath = path.join(self.FIGHTING_FX_DIR, filename)
            self.sounds.append(cached_loader.load_byte(realpath))

    @property
    def name(self):
        return "Batte pour frapper %s" % self.target_name

    def use(self, obj_params):
        # checking if target user is present, sending a notif and a sound
        if self.targeted_userid in self.channel.users:
            if self.remaining_hits > 0:
                self.notify_channel(msg=f"{self.user_fullname} donne un coup de batte à {self.target_name}",
                                    binary_payload=random.choice(self.sounds))
            self.remaining_hits -= 1
        else:
            self.notify_serv(msg=f"Cette batte ne sert qu'à taper {self.target_name}")

        # if it's the last hit, notifying and destroying the object
        if self.remaining_hits <= 0:
            self.should_be_destroyed = True
            self.notify_channel(msg=f"{self.user_fullname} a cassé sa batte sur {self.target_name}",
                                binary_payload=cached_loader.load_byte(self.BROKEN_BAT_FX))


@destructible
class Crown(LoultObject):
    NAME = "Couronne du loult"
    ICON = "crown.gif"

    class ServantEffect(ExplicitTextEffect):
        TIMEOUT = 300
        SUFFIXES = ["seigneur %s", "maître %s", "mon roi", "mon bon %s", "ô grand %s", "sire %s",
                    "sieur %s", "vénérable %s", "%s, roi du loult", "%s maître des bibwe"]

        def __init__(self, pokename):
            super().__init__()
            self.suffixes = [suff % pokename if "%s" in suff else suff for suff in self.SUFFIXES]

        def process(self, text: str):
            return text.strip("!,.:?") + ", " + random.choice(self.suffixes)

    def use(self, obj_params):
        for user in self.channel.users.values():
            if user is not self.user:
                user.state.add_effect(self.ServantEffect(self.user.poke_params.pokename))
        self.notify_channel(msg=f"{self.user_fullname} est maintenant le roi du loult")
        self.should_be_destroyed = True


@targeted()
@destructible
class ScrollOfQurk(LoultObject):
    NAME = "Parchemin du Qurk"
    ICON = "question.gif"

    class DuckEffect(ExplicitTextEffect):
        TIMEOUT = 300

        def process(self, text: str):
            return re.sub(r"[\w]+", "qurk", text)

    def use(self, obj_params):
        if random.randint(1, 5) == 1:
            target = self.user
            self.notify_channel(msg=f"{self.user_fullname} a mal lu le parchemin du Qurk et s'est changé en canard!")
        else:
            target = self.targeted_user
            self.notify_channel(msg=f"{self.user_fullname} a changé {target.poke_params.fullname} en canard!")

        target.state.add_effect(self.DuckEffect())
        params = self.target_user.poke_params
        params.img_id = "qurk"
        params.pokename = "Qurkee"
        target._info = None
        self.channel.update_userlist()


@targeted()
@destructible
class Scolopamine(LoultObject):
    NAME = "Scolopamine"
    ICON = "scolopamine.gif"

    def use(self, obj_params):
        self.user.state.inventory.objects += self.targeted_user.state.inventory.objects
        self.targeted_user.state.inventory.objects = []
        self.targeted_user.state.add_effect(GrandSpeechMasterEffect())

        self.notify_channel(msg=f"{self.user.poke_params.fullname} a drogué {self.targeted_user.poke_params.fullname} et puis a piqué tout son inventaire!")
        self.should_be_destroyed = True


@destructible
@targeted(mandatory=False)
class AlcoholBottle(LoultObject):
    NAME = "Bouteille d'alcool"
    ICON = "alcohol.gif"
    EFFECTS = [GrandSpeechMasterEffect, StutterEffect, VocalDyslexia, VowelExchangeEffect]
    FILLING_MAPPING = {0: "vide", 1: "presque vide", 2: "moitié vide",
                       3: "presque pleine", 4: "pleine"}
    BOTTLE_FX = path.join(DATA_PATH, "broken_bottle.mp3")
    GULP_FX = path.join(DATA_PATH, "gulp.mp3")
    ALCOHOLS = yaml.safe_load(open(path.join(DATA_PATH, "alcohols.yml")))

    def __init__(self):
        super().__init__()
        self.remaining_use = 4
        rnd_alc = random.choice(self.ALCOHOLS)
        self.alc_type = rnd_alc["name"]
        self.alc_brand = random.choice(rnd_alc["brands"])

    @property
    def name(self):
        if self.alc_type:
            return "Bouteille de %s %s (%s)" % (self.alc_type, self.alc_brand,
                                                self.FILLING_MAPPING[self.remaining_use])
        else:
            return "Bouteille de %s (%s)" % (self.alc_brand, self.FILLING_MAPPING[self.remaining_use])

    def use(self, obj_params):
        # user decides to use it on someone else, meaning throwing it
        if self.targeted_user is not None:
            target_dist = userlist_dist(self.channel, self.user.user_id, self.targeted_userid)
            if target_dist > 1:
                self.notify_serv(msg="Trop loin pour lancer la bouteille dessus!")
                return

            if self.targeted_user is self.user:
                msg = f"{self.user_fullname} se casse une {self.name} su'l'crâne!"
            else:
                msg = f"{self.user.poke_params.fullname} lance une {self.name} sur {self.targeted_user.poke_params.fullname}!"

            self.notify_channel(msg=msg, binary_payload=self._load_byte(self.BOTTLE_FX))
            self.targeted_user.disconnect_all_clients(code=4006, reason="Reconnect please")
            self.should_be_destroyed = True
        else:
            if self.remaining_use <= 0:
                return self.notify_serv(msg="La bouteille est vide!")
            self.notify_channel(msg=f"{self.user.poke_params.fullname} se descend un peu de {self.alc_brand}!",
                                binary_payload=self._load_byte(self.GULP_FX))
            for effect_type in self.EFFECTS:
                self.user.state.add_effect(effect_type())
            self.remaining_use -= 1


class Microphone(LoultObject):
    MIKEDROP_FX = path.join(DATA_PATH, "mikedrop.mp3")
    NAME = 'micro'
    ICON = "micro.gif"

    def use(self, obj_params):
        self.notify_channel(msg=f"{self.user.poke_params.fullname} drop le mike!",
                            binary_payload=self._load_byte(self.MIKEDROP_FX))
        self.user.disconnect_all_clients(code=4006, reason='Mike drop, bitch')


@inert
class C4(LoultObject):
    NAME = "C4"
    ICON = "c4.gif"


class Detonator(LoultObject):
    NAME = "Détonateur"
    ICON = "detonator.gif"
    EXPLOSION_FX = path.join(DATA_PATH, "explosion.mp3")

    def use(self, obj_params):
        # TODO : add fumble where the detonator blows up the user
        blown_up_users = []
        for user in self.channel.users.values():
            if user.state.inventory.search_by_class(C4):
                user.state.inventory.remove_by_class(C4)
                for client in user.clients:
                    client.send_json(type="notification",
                                     msg="%s vous a fait sauter" % self.user.poke_params.fullname)
                    client.send_binary(self._load_byte(self.EXPLOSION_FX))
                    client.sendClose(code=4006, reason='reconnect later')
                blown_up_users.append(user.poke_params.fullname)
        if blown_up_users:
            self.notify_channel(msg=f"{self.user_fullname} a fait sauter {', '.join(blown_up_users)}!",
                                binary_payload=self._load_byte(self.EXPLOSION_FX))


@destructible
class SuicideJacket(LoultObject):
    NAME = "ceinture d'explosif"
    ICON = "suicide.gif"
    EXPLOSION_FX = path.join(DATA_PATH, "suicide_bomber.mp3")

    def use(self, obj_params):
        hit_usrs = [usr for usr in self.channel.users.values()
                    if userlist_dist(self.channel, self.user.user_id, usr.user_id) < 3
                    and usr is not self.user]

        self.notify_channel(msg=f"{self.user.poke_params.fullname} s'est fait sauter, emportant avec lui {', '.join([usr.poke_params.fullname for usr in hit_usrs])}",
                            binary_payload=self._load_byte(self.EXPLOSION_FX))

        for user in hit_usrs:
            user.disconnect_all_clients(code=4006, reason="Reconnect please")
        self.channel.broadcast(type='antiflood', event='banned',
                               flooder_id=self.user.user_id,
                               date=timestamp() * 1000)
        self.loult_state.ban_cookie(self.user.cookie_hash)
        self.user.disconnect_all_clients(code=4006, reason='Reconnect later')
        self.should_be_destroyed = True

@cooldown(30)
class Costume(LoultObject):
    NAME = "costume"

    CHARACTERS = ["link", "mario", "wario", "sonic"]

    def __init__(self):
        super().__init__()
        self.character = random.choice(self.CHARACTERS)  # type:str

    @property
    def icon(self):
        return self.character + ".gif"

    @property
    def name(self):
        return self.NAME + " de %s" % self.character.capitalize()

    def use(self, obj_params):
        if hasattr(self.user, "costume") and self.user.costume == self.character:
            return self.notify_serv(
                msg="Vous ne pouvez pas enfiler deux fois d'affilée le costume!")

        self.notify_channel(msg=f"{self.user.poke_params.fullname} enfile un costume de {self.character.capitalize()}")
        params = self.user.poke_params
        params.img_id = self.character
        params.pokename = self.character.capitalize()
        self.user._info = None
        self.user.costume = self.character
        self.channel.update_userlist()


@targeted(mandatory=False)
@destructible
class RectalExam(LoultObject):
    NAME = "examen rectal"
    ICON = "rectalexam.gif"

    def use(self, obj_params):
        from ..objects import get_random_object
        rdm_objects = [get_random_object() for _ in range(random.randint(2, 4))]
        for obj in rdm_objects:
            self.user.state.inventory.add(obj)
        names_list = ", ".join(obj.name for obj in rdm_objects)

        if self.targeted_user is self.user:
            msg = f"{self.user.poke_params.fullname} a sorti {names_list} de son cul!"
        else:
            msg = f"{self.user_fullname} fouille dans le cul de {self.targeted_user.poke_params.fullname} et trouve {names_list}! "

        self.channel.broadcast(type="notification", msg=msg)
        self.should_be_destroyed = True


@targeted()
@cooldown(30)
class WealthDetector(LoultObject):
    NAME = "détecteur de richesse"
    ICON = "detector.gif"

    def use(self, obj_params):
        self.notify_channel(msg=f"{self.user_fullname} utilise le détecteur de richesse sur {self.targeted_user.poke_params.fullname}")
        self.notify_serv(msg=f"{self.targeted_user.poke_params.fullname} a {len(self.targeted_user.state.inventory.objects):d} objets dans son inventaire")


@destructible
@cooldown(5)
class Cigarettes(LoultObject):
    NAME = "cigarettes"
    ICON = "cigarettes.gif"
    BRANDS = ["Lucky Loult", "Lucky Loult Menthol", "Mrleboro", "Chesterfnre", "Sheitanes Maïs",
              "Aguloises"]
    CIG_FX = path.join(DATA_PATH, "cigarette_lighting.mp3")

    def __init__(self):
        super().__init__()
        self.brand = random.choice(self.BRANDS)
        self.cigarettes = 20

    @property
    def name(self):
        return self.brand + " (%i)" % self.cigarettes

    @property
    def destroy(self):
        return self.cigarettes <= 0

    def use(self, obj_params):
        if not self.user.state.inventory.search_by_class(Lighter):
            return self.notify_serv(
                msg="Il vous faut un briquet pour pouvoir allumer une clope!")

        self.cigarettes -= 1
        self.channel.broadcast(type="notification",
                               msg="%s allume une clope et prend un air cool"
                                   % self.user.poke_params.fullname,
                               binary_payload=self._load_byte(self.CIG_FX))
        if random.randint(1, 10) == 1:
            self.channel.broadcast(type="notification",
                                   msg="%s choppe le cancer et meurt sur le champ!"
                                       % self.user.poke_params.fullname)
            for client in self.user.clients:
                client.sendClose(code=4006, reason="Reconnect please.")


@cooldown(30)
class Lighter(LoultObject):
    NAME = "briquet"
    ICON = "lighter.gif"
    CIG_FX = path.join(DATA_PATH, "lighter.mp3")

    def use(self, obj_params):
        self.channel.broadcast(binary_payload=self._load_byte(self.CIG_FX))


@destructible
class MollyChute(LoultObject):
    NAME = "paras de MD"
    ICON = "paraMd.gif"

    class MDMAEffect(ExplicitTextEffect):
        NAME = "un paras"
        love_sentence = [
            "Attendez je vais kiffer le son là",
            "J'ai envie de vous faire un calin à tous",
            "Je peux t'embrasser %s?",
            "Vous êtes tous vraiment trop sympa en fait",
            "C'est tout doux quand je te caresse les cheveux %s",
            "Arrêtez de vous dire des trucs méchants moi je vous aime tous",
            "Franchement le monde est trop beau",
            "T'es vraiment trop sympa en fait %s",
            "C'est vraiment la plus belle soirée de ma vie",
            "t'as pas un chewing gum %s?",
            "attends faut que j'aille boire de l'eau"
        ]
        bad_trip_sentences = [
            "plus jamais je me défonce comme ça, c'est vraiment trop de la merde",
            "la vie est si nulle",
            "tellement la flemme de faire quoi que soit, marre de tout",
            "franchement ça sert à rien de sortir comme ça, dépenser son argent et se niquer la santé pour quelques heures de bonheur artificiel",
            "vraiment la descente je supporte plus, faut que j'arrête ces conneries",
            "je suis sûr que tu me détestes en fait %s",
            "j'ai trop chaud d'un coup",
            "mes parents doivent avoir honte de moi"
        ]
        TIMEOUT = 300
        # 100 last seconds are bad trippin'
        BAD_TRIP_TIME = 200

        def __init__(self, users_names):
            super().__init__()
            self.users = users_names
            self.start = datetime.now()

        def process(self, text: str):
            if random.randint(1, 3) == 1:
                if (datetime.now() - self.start).seconds < self.BAD_TRIP_TIME:
                    sentence = random.choice(self.love_sentence)
                else:
                    sentence = random.choice(self.bad_trip_sentences)

                if "%s" in sentence:
                    return sentence % random.choice(self.users)
                else:
                    return sentence
            else:
                return text

    def use(self, obj_params):
        efct = self.MDMAEffect([usr.poke_params.pokename for usr in self.channel.users.values()])
        self.user.state.add_effect(efct)
        self.channel.broadcast(type="notification",
                               msg="%s prend de la MD!" % self.user.poke_params.fullname)
        self.should_be_destroyed = True


@destructible
class CaptainHaddockPipe(LoultObject):
    NAME = "pipe du capitaine haddock"
    ICON = "haddockpipe.gif"

    def use(self, obj_params):
        self.user.state.add_effect(CaptainHaddockEffect())
        self.channel.broadcast(type="notification",
                               msg="%s est un marin d'eau douce!" % self.user.poke_params.fullname)
        self.should_be_destroyed = True


