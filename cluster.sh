#!/bin/env sh

# export requirements.txt
if command -v pdm &> /dev/null; then
  echo "pdm found, exporting requirements.txt"
  pdm export --format requirements > requirements.txt
else
  echo "pdm not found, using already existing requirements.txt"
fi

# backup cluster.zip
if [ -f "cluster.zip" ]; then
  i=1
  while [ -f "cluster.zip.back.$i" ]; do
    ((i++))
  done
  mv "cluster.zip" "cluster.zip.back.$i"
fi


zip -r cluster.zip $(find . -type f | grep -vE 'cluster.zip*|__pycache__|~$|\.log$|\.pkl$|^output$|^humdrum-tools$|^\./\.')
