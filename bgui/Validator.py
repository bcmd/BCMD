# simple validator for strings entered in BGUI
import re

ID_REGEX = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def is_valid_id(s):
    return bool(ID_REGEX.match(s))


    