#!/bin/sh

# Command to check everything works
python -m symbolic_features.effectiveness classification --featureset=$1 --dataset=$2 --extension=$3 --keep_first_10_pc=$4 2>&1 | tee -a $5

# Command to run all the experiments
# featuresets="musif musif_native music21 music21_native jsymbolic musif_native-jsymbolic musif_native-music21_native music21_native-jsymbolic musif_native-music21_native-jsymbolic"
# datasets="asap-scores asap-performances didone EWLD JLR quartets"
# extensions="mid xml krn"
# pca_list="True False"

# for pca in $pca_list; do
#   for featureset in $featuresets; do
#     for dataset in $datasets; do
#       for extension in $extensions; do
#         echo "-----------------" | tee $1
#         echo "Experiment started: $pca $featureset $dataset $extension" | tee $1
#   			python -m symbolic_features.effectiveness classification --featureset=$featureset --dataset=$dataset --extension=$extension --keep_first_10_pc=$pca 2>&1 | tee -a $1
#         echo "Experiment ended" | tee $1
#         echo "-----------------" | tee $1
#       done
# 		done
# 	done
# done
