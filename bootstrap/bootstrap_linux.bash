#!/bin/bash

# This script is used to setup a linux box for use with PyExpLabSys

##############################################################
# EDIT POINT START: Edit here to change what the script does #
##############################################################

# Usage string, edit if adding another section to the script
usage="This is the SurfCat Linux bootstrap script

    USAGE: bootstrap_linux.bash SECTION

Where SECTION is the part of the bootstrap script that you want to run, listed below. If the value of \"all\" is given all section will be run - this should be done for a fresh install. NOTE you can only supply one argument:

Sections:
bash        Edit PATH and PYTHONPATH in .bashrc to make PyExpLabSys scripts
            runnable and PyExpLabSys importable. Plus add bash aliasses for
            most common commands including apt commands.
git         Add common git aliases
install     Install commonly used packages e.g openssh-server
pip         Install extra Python packages with pip
autostart   Setup autostart cronjob
settings    Link in the SurfCat PyExpLabSys settings file
screen      Visual defaults for screen program

all         All of the above
"
##################
# EDIT POINT END #
##################

# Functions
echobad(){
    echo -e "\033[1m\E[31m$@\033[0m"
}

echobold(){
    echo -e "\033[1m$@\033[0m"
}

echogood(){
    echo -e "\033[1m\E[32m$@\033[0m"
}

echoblue(){
    echo -e "\033[1m\E[34m$@\033[0m"
}

echoyellow(){
    echo -e "\033[1m\E[33m$@\033[0m"
}

# Checks argument number and if needed print usage
if [ $# -eq 0 ] || [ $# -gt 1 ];then
    echo "$usage"
    exit
fi

if [ $1 == "bash" ] || [ $1 == "all" ];then
    $HOME/PyExpLabSys/bootstrap/bootstrap_linux.bash bash
fi

# Git section
if [ $1 == "git" ] || [ $1 == "all" ];then
    $HOME/PyExpLabSys/bootstrap/bootstrap_linux.bash git
fi

# Install packages
if [ $1 == "install" ] || [ $1 == "all" ];then
    $HOME/PyExpLabSys/bootstrap/bootstrap_linux.bash install
fi

# Install extra packages with pip
if [ $1 == "pip" ] || [ $1 == "all" ];then
    $HOME/PyExpLabSys/bootstrap/bootstrap_linux.bash pip
fi

# Setup autostart cronjob
if [ $1 == "autostart" ] || [ $1 == "all" ];then
    $HOME/PyExpLabSys/bootstrap/bootstrap_linux.bash autostart
fi

# Setup settings file for PyExpLabSys
if [ $1 == "settings" ] || [ $1 == "all" ];then
    echobold "===> SETTING UP A PYEXPLABSYS SETTINGS FILE"
    if [ -f ~/.config/PyExpLabSys/user_settings.yaml ];then
        echogood "Settings file already exists - remove if you want to overwrite it"
    else
        echoblue "---> Make ~/.config/PyExpLabSys dir"
        mkdir -p ~/.config/PyExpLabSys
        echoblue "---> Link settings into dir:"
        echoblue "---> ~/machines/bootstrap/user_settings.yaml into ~/.config/PyExpLabSys/"
        cp ~/machines/bootstrap/user_settings.yaml ~/.config/PyExpLabSys/user_settings.yaml
    fi
    echogood "+++++> DONE"
fi

# Setup autostart cronjob
if [ $1 == "screen" ] || [ $1 == "all" ];then
    $HOME/PyExpLabSys/bootstrap/bootstrap_linux.bash screen
fi
