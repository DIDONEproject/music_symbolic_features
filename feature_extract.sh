#!/bin/bash

# Xvfb :99 & export DISPLAY=:99

convert_to_midi() {
  # convert and musicxml to midi using musescore
  for f in $(find $1 -name "*.$2")
  do
    echo "Converting file $f"
    mscore -fo ${f/.$2/.mid} $f
  done

}

for dataset in $(ls datasets)
do
  if test -d datasets/$dataset
  then
    convert_to_midi datasets/$dataset mxl
    convert_to_midi datasets/$dataset xml
    convert_to_midi datasets/$dataset musicxml

    echo "Extracting features from $dataset"
    mkdir -p features/$dataset
    java -jar ./tools/jSymbolic_2_2_user/jSymbolic2.jar -csv $(realpath datasets/$dataset) features/$dataset/jsymbolic features/$dataset/jsymbolic_def
  fi
done


