#!/usr/bin/python3

import os
import sys

real_args = ['emacs' ]
for x in sys.argv[1:] :
    colon_pos = x.find(':')
    if colon_pos == -1 :      # no colons
        if (x[-1] == '.') :
            real_args.append(x + "h")
            real_args.append(x + "cpp")
        else :
            real_args.append(x)
    else :                      # colon somewhere
        bits = x.split(':',1)
        line_arg = bits[1]
        filename = bits[0]
        if (len(line_arg) > 0) : # if not true, we just ignore line_arg
            if line_arg[-1] == ':' : # strip any trailing ':'
                line_arg = line_arg[:-1]
            real_args.append('+' + line_arg)
        real_args.append(filename)

print(real_args)

os.execvp('emacs', real_args)
