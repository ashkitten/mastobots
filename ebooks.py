from ananas import PineappleBot, daily, hourly, interval, reply
from ananas import html_strip_tags
from distutils.util import strtobool
from mastodon import Mastodon
import getopt
import html
import json
import markovify
import os
import re
import sys


class ZeroText(markovify.Text):
    def sentence_split(self, text):
        return text.split("\0")


class EbooksBot(PineappleBot):
    exclude_replies = True
    model = None

    def start(self):
        if self.config.exclude_replies:
            self.exclude_replies = strtobool(self.config.exclude_replies)
        self.scrape()

    # scrapes the accounts the bot is following to build corpus
    @daily(hour=4, minute=20)
    def scrape(self):
        me = self.mastodon.account_verify_credentials()
        following = self.mastodon.account_following(me["id"])
        acctfile = "accts.json"
        # acctfile contains info on last scraped toot id
        try:
            with open(acctfile, "r") as f:
                acctjson = json.load(f)
        except BaseException:
            acctjson = {}

        self.log("scrape", acctjson)
        for acc in following:
            id = str(acc["id"])
            try:
                acctjson[id] = self.scrape_id(id, since=acctjson[id])
            except KeyError:
                acctjson[id] = self.scrape_id(id)

        with open(acctfile, "w") as f:
            json.dump(acctjson, f)

        # generate the whole corpus after scraping so we don't do at every
        # runtime
        for (dirpath, _, filenames) in os.walk("corpus"):
            for filename in filenames:
                with open(os.path.join(dirpath, filename)) as f:
                    model = ZeroText(f)
                    if self.model is not None:
                        self.model = markovify.combine(
                            models=[self.model, model])
                    else:
                        self.model = model

    def scrape_id(self, id, since=None):
        # excluding replies was a personal choice. i haven't made an easy
        # setting for this yet
        toots = self.mastodon.account_statuses(
            id, since_id=since, exclude_replies=self.exclude_replies)
        # if this fails, there are no new toots and we just return old pointer
        try:
            since = toots[0]["id"]
        except IndexError:
            return since

        buffer = ""
        while toots is not None:
            for toot in toots:
                if (toot["spoiler_text"] == ""
                        and toot["reblog"] is None
                        and toot["visibility"] in ["public", "unlisted"]):
                    buffer += html_strip_tags(toot["content"], linebreaks=True).strip() + "\0"
            toots = self.mastodon.fetch_next(toots)

        corpusfile = "corpus/{}.txt".format(id)

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

    # scan all notifications for mentions and reply to them
    @reply
    def on_reply(self, mention, user):
        msg = html_strip_tags(mention["content"], linebreaks=True)
        self.log("on_reply", "Received toot from {}: \"{}\"".format(
            user["acct"], msg))

        if "!delete" in msg and user["acct"] == self.config.admin:
            self.log("on_reply", "Deleting toot: {}".format(
                mention["in_reply_to_id"]))
            self.mastodon.status_delete(mention["in_reply_to_id"])
            return

        matches = re.search("(?:gimme|can i get)(?: some)?(?: uh+)? (\w+)", msg)
        if matches is not None:
            for _ in range(100):
                response = self.model.make_sentence_with_start(matches.group(1), strict=False, tries=100)
                if response and len(response) <= 400:
                    break
        else:
            response = self.model.make_short_sentence(400, tries=100)

        self.log("on_reply", "Responding with \"{}\", visibility: {}".format(
            mention["visibility"], response))
        response = "@{} {}".format(user["acct"], response)[:500]
        self.mastodon.status_post(
            response,
            in_reply_to_id=mention["id"],
            visibility=mention["visibility"])
