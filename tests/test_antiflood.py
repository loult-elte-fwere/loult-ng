import unittest

from config import FLOOD_DETECTION_MSG_PER_SEC, FLOOD_DETECTION_WINDOW
from loult_serv.state_users import UserState


class TestUserState(unittest.TestCase):

    def test_is_flooding(self):
        user_state = UserState()
        # sending an average of X messages per Y seconds means
        # having sent X*Y messages in Y seconds.
        flood_nb = FLOOD_DETECTION_MSG_PER_SEC * FLOOD_DETECTION_WINDOW
        for i in range(flood_nb):
            self.assertFalse(user_state.check_flood(''))
        self.assertTrue(user_state.check_flood(''))

    def test_is_flooding_no_trigger(self):
        user_state = UserState()
        # sending an average of X messages per Y seconds means
        # having sent X*Y messages in Y seconds.
        flood_nb = FLOOD_DETECTION_MSG_PER_SEC * FLOOD_DETECTION_WINDOW
        for i in range(flood_nb):
            self.assertFalse(user_state.check_flood(''))

    def test_banned_words(self):
        word_list = [".*stuff.*", "^[0-9]{2}.*"]
        user_state = UserState(banned_words=word_list)
        self.assertTrue(user_state.censor("something stuff and things"))
        self.assertFalse(user_state.censor("something stuf and things"))
        self.assertTrue(user_state.censor("10 something"))
        self.assertFalse(user_state.censor("1 something"))


if __name__ == "__main__":
    unittest.main()
