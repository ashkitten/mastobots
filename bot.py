from ananas import PineappleBot
import sys


class Bot(PineappleBot):
    def log(self, id, msg):
        if (id == None): id = self.name
        else: id = self.name + "." + id
        msg_f = "{}: {}".format(id, msg)

        if self.log_file.closed or self.log_to_stderr: print(msg_f, file=sys.stderr)
        elif not self.log_file.closed: print(msg_f, file=self.log_file)
