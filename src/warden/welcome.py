import emoji
from ansi.colour import fg


def logo():
    print(
        fg.brightgreen(f"""
  _   _           __        ___    ____     _
 | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
 | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
 | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
  \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|"""))
    print("")
    print(
        emoji.emojize(
            "                                      Specter Edition :ghost:"))
    print(
        fg.yellow(
            "                             Powered by NgU technology ₿"))
