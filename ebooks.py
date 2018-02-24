from ananas import daily, hourly, interval, reply, html_strip_tags
from bot import Bot
from distutils.util import strtobool
from mastodon import Mastodon
import fileinput
import getopt
import html
import json
import markovify
import os
import re
import sys
import time


class ZeroText(markovify.Text):
    def sentence_split(self, text):
        return text.split("\0")


class EbooksBot(Bot):
    exclude_replies = True
    max_replies = 3
    recent_replies = {}

    def start(self):
        if "exclude_replies" in self.config:
            self.exclude_replies = strtobool(self.config.exclude_replies)
        if "max_replies" in self.config:
            self.max_replies = int(self.config.max_replies)

        self.scrape()

    # scrapes the accounts the bot is following to build corpus
    @daily(hour=4, minute=20)
    def scrape(self):
        self.log("scrape", "starting scrape")

        me = self.mastodon.account_verify_credentials()
        following = self.mastodon.account_following(me["id"])
        acctfile = "accts.json"
        # acctfile contains info on last scraped toot id
        try:
            with open(acctfile, "r") as f:
                acctjson = json.load(f)
        except BaseException:
            acctjson = {}

        self.corpus = ""
        for account in following:
            account_id = str(account["id"])
            try:
                acctjson[account_id] = self.scrape_account(account_id, since=acctjson[account_id])
            except KeyError:
                acctjson[account_id] = self.scrape_account(account_id)

            # dump now in case it gets interrupted
            with open(acctfile, "w") as f:
                json.dump(acctjson, f)

            with open("corpus/{}.txt".format(account["id"])) as f:
                self.corpus += f.read()

        self.log("scrape", "scraped all following, regenerating model")

        # generate the whole corpus after scraping so we don't do at every
        # runtime
        self.model = ZeroText(self.corpus)

        self.log("scrape", "regenerated model")

    def scrape_account(self, account, since=None):
        # excluding replies was a personal choice. i haven't made an easy
        # setting for this yet
        toots = self.mastodon.account_statuses(
            account, since_id=since, exclude_replies=self.exclude_replies)
        # if this fails, there are no new toots and we just return old pointer
        try:
            since = toots[0]["id"]
        except IndexError:
            return since

        count = 0
        buffer = ""
        while toots is not None and len(toots) > 0:
            for toot in toots:
                if (toot["spoiler_text"] == "" and toot["reblog"] is None
                        and toot["visibility"] in ["public", "unlisted"]):
                    content = html_strip_tags(toot["content"], linebreaks=True).strip() + "\0"
                    if re.search("@\w", content) is None:
                        buffer += content
                        count += 1
            toots = self.mastodon.fetch_next(toots)

        self.log("scrape_account", "scraped {} toots from {}".format(count, account))

        corpusfile = "corpus/{}.txt".format(account)

        directory = os.path.dirname(corpusfile)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # buffer is appended to the top of old corpus
        try:
            f = open(corpusfile, "r+")
            buffer += f.read()
            f.seek(0)
        except OSError:
            f = open(corpusfile, "a+")
        f.write(buffer)
        f.truncate()

        return since

    # perform a generated toot to mastodon
    @hourly(minute=23)
    def toot(self):
        msg = self.model.make_short_sentence(500, tries=100)
        self.mastodon.toot(msg)
        self.log("toot", "Tooted: {}".format(msg))

    def reply_toot(self, mention, user, response):
        if (user["id"] in self.recent_replies and
                not user["acct"] == self.config.admin and
                self.recent_replies[tgt] < self.max_replies):
            self.log("reply_toot", "I've talked to them too much recently")
            return

        self.log("reply", "Responding with \"{}\", visibility: {}".format(
            response, mention["visibility"]))
        response = "@{} {}".format(user["acct"], response)[:500]
        self.mastodon.status_post(
            response,
            in_reply_to_id=mention["id"],
            visibility=mention["visibility"])

        try:
            self.recent_replies[user["id"]] += 1
        except KeyError:
            self.recent_replies[user["id"]] = 1

    # scan all notifications for mentions and reply to them
    @reply
    def on_reply(self, mention, user):
        msg = html_strip_tags(mention["content"], linebreaks=True)
        self.log("on_reply", "Received toot from {}: \"{}\"".format(user["acct"], msg))

        if "!delete" in msg and user["acct"] == self.config.admin:
            self.log("on_reply", "Deleting toot: {}".format(mention["in_reply_to_id"]))
            self.mastodon.status_delete(mention["in_reply_to_id"])
            return

        if "!followme" in msg:
            self.mastodon.account_follow(user["id"])
            self.reply_toot(mention, user, "kapow!")
            time.sleep(60)
            self.scrape()
            return

        if "!unfollowme" in msg:
            self.mastodon.account_unfollow(user["id"])
            self.reply_toot(mention, user, "kabam!")
            time.sleep(60)
            self.scrape()
            return

        matches = re.search(
            "(?:gimme|can i get)(?: some| a)?(?: uh+)? (\")?(?P<s>(?(1).*(?=\")|\w+))",
            msg, flags=re.IGNORECASE)
        if matches is not None:
            s = matches.group("s")
            if s.lower() in self.corpus.lower():
                while True:
                    response = self.model.make_short_sentence(400, tries=100)
                    if s.lower() in response.lower():
                        break
            else:
                response = "no."
        else:
            response = self.model.make_short_sentence(400, tries=100)

        self.reply_toot(mention, user, response)
