from ananas import daily, hourly, interval, reply, html_strip_tags
from bot import Bot
from distutils.util import strtobool
from mastodon import Mastodon
from mastodon.Mastodon import MastodonNotFoundError
import fileinput
import getopt
import html
import json
import markovify
import os
import re
import sys


class EbooksBot(Bot):
    exclude_replies = True
    max_replies = 5
    recent_replies = {}

    def start(self):
        if "exclude_replies" in self.config:
            self.exclude_replies = strtobool(self.config.exclude_replies)
        if "max_replies" in self.config:
            self.max_replies = int(self.config.max_replies)

        self.scrape()

    # scrapes the accounts the bot is following to build corpus
    @hourly(minute=0)
    def scrape(self):
        self.log("scrape", "starting scrape")

        me = self.mastodon.account_verify_credentials()
        following = self.mastodon.account_following(me.id)
        acctfile = "accts.json"
        # acctfile contains info on last scraped toot id
        try:
            with open(acctfile, "r") as f:
                acctjson = json.load(f)
        except BaseException:
            acctjson = {}

        self.log("scrape", "Accounts: {}".format(json.dumps(acctjson, sort_keys=True, indent=4)))

        self.corpus = ""
        for account in following:
            try:
                since = self.mastodon.status(acctjson[str(account.id)]).id
                acctjson[str(account.id)] = self.scrape_account(account.id, since=since)
                with open("corpus/{}.txt".format(account.id), "r") as f:
                    self.corpus += f.read()
            except (KeyError, MastodonNotFoundError):
                acctjson[str(account.id)] = self.scrape_account(account.id)

            # dump now in case it gets interrupted
            with open(acctfile, "w") as f:
                json.dump(acctjson, f)

        self.log("scrape", "scraped all following, regenerating model")

        # generate the whole corpus after scraping so we don't do at every
        # runtime
        self.model = markovify.NewlineText(self.corpus)

        self.log("scrape", "regenerated model")

    def scrape_account(self, account, since=None):
        # excluding replies was a personal choice. i haven't made an easy
        # setting for this yet
        toots = self.mastodon.account_statuses(
            account, since_id=since, exclude_replies=self.exclude_replies)
        # if this fails, there are no new toots and we just return old pointer
        try:
            since = toots[0].id
        except IndexError:
            return since

        total = 0
        count = 0
        buffer = ""
        while toots is not None and len(toots) > 0:
            for toot in toots:
                total += 1
                if (toot.spoiler_text == "" and toot.reblog is None
                        and toot.visibility in ["public", "unlisted"]):
                    content = html_strip_tags(toot.content, linebreaks=True).strip() + "\n"
                    if re.search("@\w", content) is None:
                        buffer += content
                        count += 1
            toots = self.mastodon.fetch_next(toots)

        self.log("scrape_account", "scraped {} toots from {}".format(total, account))
        self.log("scrape_account", "added {} toots to the corpus".format(count, account))

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
        f.close()

        return since

    # perform a generated toot to mastodon
    @hourly(minute=23)
    def toot(self):
        msg = self.model.make_short_sentence(500, tries=100)
        self.mastodon.toot(msg)
        self.log("toot", "Tooted: {}".format(msg))

    def reply_toot(self, mention, user, response):
        if (user.id in self.recent_replies and
                not user.acct == self.config.admin and
                self.recent_replies[user.id] < self.max_replies):
            self.log("reply_toot", "I've talked to them too much recently")
            return

        self.log("reply", "Responding with \"{}\", visibility: {}".format(
            response, mention.visibility))
        response = "@{} {}".format(user.acct, response)[:500]
        self.mastodon.status_post(
            response,
            in_reply_to_id=mention.id,
            visibility=mention.visibility)

        try:
            self.recent_replies[user.id] += 1
        except KeyError:
            self.recent_replies[user.id] = 1

    @interval(30)
    def clear_replies(self):
        self.recent_replies = {}

    # scan all notifications for mentions and reply to them
    @reply
    def on_reply(self, mention, user):
        msg = html_strip_tags(mention.content, linebreaks=True)
        self.log("on_reply", "Received toot from {}: \"{}\"".format(user.acct, msg))

        if "!delete" in msg and user.acct == self.config.admin:
            self.log("on_reply", "Deleting toot: {}".format(mention.in_reply_to_id))
            self.mastodon.status_delete(mention.in_reply_to_id)
            return

        if "!followme" in msg:
            self.mastodon.account_follow(user.id)
            self.reply_toot(mention, user, "kapow!")
            return

        if "!unfollowme" in msg:
            self.mastodon.account_unfollow(user.id)
            self.reply_toot(mention, user, "kabam!")
            return

        matches = re.search(
            r"(?:gimme|can i get)(?: some| a)?(?: uh+)? (\")?(?P<s>(?(1).*(?=\")|\w+))",
            msg, flags=re.IGNORECASE)
        if matches is not None:
            s = matches.group("s")
            if s in self.corpus:
                response = "too lazy, giving up."
                for _ in range(0, 100):
                    r = self.model.make_short_sentence(400, tries=100)
                    if s in r:
                        response = r
                        break
            else:
                response = "no."
        else:
            response = self.model.make_short_sentence(400, tries=100)

        self.reply_toot(mention, user, response)
