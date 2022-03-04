import random


def gengenerateID():
    re = ""
    for i in range(128):
        re += chr(random.randint(65, 90))
    return re