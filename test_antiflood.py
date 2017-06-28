import unittest
from datetime import datetime, timedelta
from tools.tools import UserState
from config import FLOOD_DETECTION_MSG_PER_SEC, FLOOD_DETECTION_WINDOW


class TestUserState(unittest.TestCase):

    @unittest.skip("skip")
    def tset_log_msg(self):
        user_state = UserState()
        user_state.add_to_backlog("")
        self.assertEqual(len(user_state.timestamps), 1)
        self.assertEqual(len(user_state.backlog), 1)

    def test_is_too_fast(self):
        user_state = UserState(speed_window_max=10)
        # sending an average of X messages per Y seconds means
        # having sent X*Y messages in Y seconds.
        for i in range(10):
            user_state.add_to_backlog('')
            self.assertFalse(user_state.is_too_fast)

        user_state.add_to_backlog('')
        self.assertTrue(user_state.is_too_fast)

    def test_is_flooding_no_trigger(self):
        user_state = UserState(speed_window_max=10)
        for i in range(10):
            user_state.add_to_backlog('')
            self.assertFalse(user_state.is_too_fast)

    def test_banned_words(self):
        word_list = [".*stuff.*", "^[0-9]{2}.*"]
        user_state = UserState(banned_words=word_list)
        user_state.add_to_backlog("something stuff and things")
        self.assertTrue(user_state.is_censored)

        user_state.add_to_backlog("something stuf and things")
        self.assertFalse(user_state.is_censored)

        user_state.add_to_backlog("10 something")
        self.assertTrue(user_state.is_censored)

        user_state.add_to_backlog("1 something")
        self.assertFalse(user_state.is_censored)

    def test_distance(self):
        user_state = UserState(similarity_max=0)

        user_state.add_to_backlog('a')
        self.assertFalse(user_state.is_rambling)

        user_state.add_to_backlog('aaaaaaaaaaaaaa')
        self.assertTrue(user_state.is_rambling)


if __name__ == "__main__":
    unittest.main()
