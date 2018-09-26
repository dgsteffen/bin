#!/bin/sh
 
# cypath convert the files

file1=`cygpath -w $1`
file2=`cygpath -w $2`


echo "YO: $1 $file1"

"/cygdrive/c/Program Files (x86)/Perforce/p4merge.exe"  "$file1" "$file2" am'
