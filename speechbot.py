from ananas import reply, html_strip_tags
from bot import Bot
import os
import subprocess
import tempfile

def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]

class SpeechBot(Bot):
    # scan all notifications for mentions and reply to them
    @reply
    def on_reply(self, mention, user):
        msg = html_strip_tags(mention.content, linebreaks=True)
        self.log("on_reply", "Received toot from {}: \"{}\"".format(user.acct, msg))

        if "!delete" in msg and user.acct == self.config.admin:
            self.log("on_reply", "Deleting toot: {}".format(mention.in_reply_to_id))
            self.mastodon.status_delete(mention.in_reply_to_id)
            return

        with tempfile.NamedTemporaryFile(suffix=".wav") as af:
            subprocess.check_call([
                "espeak",
                remove_prefix(msg.strip(), "@tts"),
                "-w", af.name,
            ])

            with tempfile.NamedTemporaryFile(suffix=".mp4") as vf:
                subprocess.check_call([
                    "ffmpeg",
                    "-i", af.name,
                    "-i", "speechbot.png",
                    "-profile:v", "baseline",
                    "-pix_fmt", "yuv420p",
                    "-y",
                    "-hide_banner",
                    "-nostats",
                    "-loglevel", "panic",
                    vf.name,
                ])

                self.log("on_reply", "Generated video, posting...")

                media = self.mastodon.media_post(vf.name)
                self.mastodon.status_post("@{}".format(user.acct), in_reply_to_id=mention, visibility=mention.visibility, media_ids=media)
