#!/usr/bin/python

import os
import sys

real_args = ['emacs']
for x in sys.argv[1:] :
    if x.find(':') == -1 :
        real_args.append(x)
    else :
        bits = x.split(':',1)
        line_arg = bits[1]
        filename = bits[0]
        if line_arg[-1] == ':' :
            line_arg = line_arg[:-1]
        real_args.append('+' + line_arg)
        real_args.append(filename)

#print real_args

os.execvp('/usr/bin/emacs', real_args)