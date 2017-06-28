# in seconds, the time a pokemon has to wait before being able to attack again
ATTACK_RESTING_TIME = 30

# in seconds, the time during which a users's message are "remembered"
FLOOD_DETECTION_WINDOW = 4

# number of messages per second a user has to be sending (on average, during the detection window) to get
# shadowmuted
FLOOD_DETECTION_MSG_PER_SEC = 3

SIMILARITY_DETECTION_WINDOW = 30
SIMILARITY_THRESHOLD = 70
SIMILARITY_BURST = 20
SIMILARITY_START = (2, 1)
SIMILARITY_END = (50, 10)

# duration in seconds until a warned flooder
# isn't considered a flooder anymore if they stop flooding
FLOOD_WARNING_TIMEOUT = 5 * 60

# in minutes, the time before a shadowmuted/banned user is able to connect again
BAN_TIME = 1

# Regular expressions interpreted by the "re" module and tested
# in fullmatch mode. See https://docs.python.org/3/library/re.html
# For example, [r".*\bTrump\b.*"] will match any sentence
# containing the word "Trump", but won't match "Trumped".
# For case insensitivity, use (?i) before your regex.
BANNED_WORDS = [r"(?i).*\bTrump\b.*", r"(?i).*\bfag(got)?\b.*"]

MOD_COOKIES = ["put your cookies here; not their hashes, not userids, the actual cookies' id key"]

# Name of a netfilter table with a chain whose hook is 'input' (resp. 'output')
# in which the sets 'ban' (resp. 'slowban') are present. If you use the sample
# config file for nftables you don't need to change anything here.
NFTABLES_INPUT = 'filter'
NFTABLES_OUTPUT = 'filter'
