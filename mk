#!/usr/bin/bash



while [[ ! -d build  ]]; do 
    if [[ $PWD == '/' ]]; then
        echo "No build directory found, exiting"
        exit 1
    fi
    
    echo
    echo "No build found in ${PWD}, going up"
    echo
    cd ..; 
done

cd build
make -j
