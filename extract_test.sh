#!/bin/env sh

rm -r musif_cache

pdm extract musif --extension .mid | tee musif-mid.log
pdm extract musif --extension .xml | tee musif-xml.log
pdm extract musif --extension .krn | tee musif-krn.log
