#!/bin/env sh

rm -r musif_cache

pdm extract musif --extension .mid | tee musif-mid.log
pdm extract music21 --extension .mid | tee music21-mid.log
pdm extract jsymbolic --extension .mid | tee jsymbolic-mid.log

pdm extract musif --extension .xml | tee musif-xml.log
pdm extract music21 --extension .xml | tee music21-xml.log

pdm extract musif --extension .krn | tee musif-krn.log
pdm extract music21 --extension .krn | tee music21-krn.log
