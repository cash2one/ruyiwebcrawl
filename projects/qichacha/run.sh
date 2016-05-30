#!/bin/sh

if [ $# -eq 0 ]; then
    echo "Usage: $0 test"
    exit
fi

if [ "$1" = "init" ]; then
  echo "sudo pip install virtualenvwrapper"
  echo "source /usr/local/bin/virtualenvwrapper.sh"
  echo "mkvirtualenv qichacha"
  echo "source env.sh"
  echo "pip install -r requirments.txt"
fi

if [ "$1" = "search" ]; then
  source env.sh
  python business/crawljob.py search medical
fi

if [ "$1" = "upload" ]; then
  rsync -azvrtopg -e 'ssh -p50001'  ./local  data@106.75.14.79:/data/ruyi/ruyiwebcrawl/projects/qichacha
  echo "ssh -p50001 data@106.75.14.79"
fi

if [ "$1" = "download" ]; then
  rsync -azvrtopg -e 'ssh  -p50001'   data@106.75.14.79:/data/ruyi/ruyiwebcrawl/projects/qichacha/local .
  echo "ssh -p50001 data@106.75.14.79"

fi