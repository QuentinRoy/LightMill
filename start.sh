#!/bin/sh


# Argument list for the experiment server.
serverArgList=' '
# Argument list for python.
pyArgList=''
# Check if debug mode, else activate python optimization.
debug=false



# Idiomatic parameter and option handling in sh.
while test $# -gt 0
do
    case "$1" in
        --debug) debug=true
                 serverArgList+=" $1"
            ;;
        *) serverArgList+=" $1"
            ;;
    esac
    shift
done

if [ "$debug" = false ] ; then
    pyArgList+=" -O"
fi

source ./venv/bin/activate && python $pyArgList ./start.py $serverArgList
