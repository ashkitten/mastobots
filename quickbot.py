from ananas import PineappleBot, interval, reply
from datetime import datetime
import random


class QuickBot(PineappleBot):
    def start(self):
        with open("words/nouns.txt", "r") as f:
            self.nouns = [line.rstrip("\n") for line in f]
        with open("words/verbs.txt", "r") as f:
            self.verbs = [line.rstrip("\n") for line in f]

    @interval(60)
    def toot(self):
        now = datetime.now()
        hour = now.hour % 12
        if hour == 0:
            hour = 12
        minute = now.minute

        if hour == minute:
            verb = random.choice(self.verbs)
            noun = random.choice(self.nouns)
            a = "a"
            if noun[0] in ["a", "e", "i", "o", "u"]:
                a = "an"
            msg = "it's {}:{:02}! quick, {} {} {}!".format(
                hour, minute, verb, a, noun)
            self.mastodon.toot(msg)
            self.log("toot", "Tooted: {}".format(msg))

    @reply
    def on_reply(self, mention, user):
        msg = html_strip_tags(mention["content"], linebreaks=True)
        self.log("on_reply", "Received toot from {}: {}".format(
            user["acct"], msg))

        if "!delete" in msg and user["acct"] == self.config.admin:
            self.log("on_reply", "Deleting toot: {}".format(
                mention["in_reply_to_id"]))
            self.mastodon.status_delete(mention["in_reply_to_id"])
            return
