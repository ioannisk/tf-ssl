#!/usr/bin/env bash

# GPU 1
python vat_ladder.py  --batch_size 100 --beta1 0.9 --beta1_during_decay 0.9 --cnn  --cnn_dims 32-32-16-16-16-8-8-8-1 --cnn_fan 1-32-32-64-64-64-128-10-10-10 --cnn_init_size 784 --cnn_ksizes 5-2-3-3-2-3-1-0-0 --cnn_layer_types c-max-c-c-max-c-c-avg-fc --cnn_strides 1-2-1-1-2-1-1-0-0 --dataset mnist --decay_start 0.67 --do_not_save  --end_epoch 150 --id GammaConvSmallMnist_seed-1 --logdir logs/GammaConvSmallMnist/ --lr_decay_frequency 10 --model gamma --rc_weights 1.0 --seed 1 --test_frequency_in_epochs 10 --ul_batch_size 100 --which_gpu 1

python vat_ladder.py  --batch_size 100 --beta1 0.9 --beta1_during_decay 0.9 --cnn  --cnn_dims 32-32-16-16-16-8-8-8-1 --cnn_fan 1-32-32-64-64-64-128-10-10-10 --cnn_init_size 784 --cnn_ksizes 5-2-3-3-2-3-1-0-0 --cnn_layer_types c-max-c-c-max-c-c-avg-fc --cnn_strides 1-2-1-1-2-1-1-0-0 --dataset mnist --decay_start 0.67 --do_not_save  --end_epoch 150 --id GammaConvSmallMnist_seed-11 --logdir logs/GammaConvSmallMnist/ --lr_decay_frequency 10 --model gamma --rc_weights 1.0 --seed 11 --test_frequency_in_epochs 10 --ul_batch_size 100 --which_gpu 1

python vat_ladder.py  --batch_size 100 --beta1 0.9 --beta1_during_decay 0.9 --cnn  --cnn_dims 32-32-16-16-16-8-8-8-1 --cnn_fan 1-32-32-64-64-64-128-10-10-10 --cnn_init_size 784 --cnn_ksizes 5-2-3-3-2-3-1-0-0 --cnn_layer_types c-max-c-c-max-c-c-avg-fc --cnn_strides 1-2-1-1-2-1-1-0-0 --dataset mnist --decay_start 0.67 --do_not_save  --end_epoch 150 --id GammaConvSmallMnist_seed-100 --logdir logs/GammaConvSmallMnist/ --lr_decay_frequency 10 --model gamma --rc_weights 1.0 --seed 100 --test_frequency_in_epochs 10 --ul_batch_size 100 --which_gpu 1
