
import tensorflow as tf
import os
import time
from tqdm import tqdm
from src.utils import get_cli_params, process_cli_params, \
    order_param_settings, count_trainable_params
from src.ladder import get_batch_ops, preprocess, BatchNormLayers, Encoder, \
    Decoder, gauss_combinator
from src import input_data
import numpy as np
import IPython


def main():

    params = process_cli_params(get_cli_params())

    # -----------------------------
    # Set GPU device to use
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = str(params.which_gpu)

    # -----------------------------
    # Set seeds
    np.random.seed(params.seed)
    tf.set_random_seed(params.seed)

    # -----------------------------
    print("===  Loading Data ===")
    mnist = input_data.read_data_sets("MNIST_data",
                                      n_labeled=params.num_labeled,
                                      one_hot=True,
                                      disjoint=False)

    # -----------------------------
    # Parameter set up
    # -----------------------------
    num_examples = mnist.train.num_examples

    starter_learning_rate = params.initial_learning_rate

    # epoch after which to begin learning rate decay
    decay_after = params.decay_start_epoch
    batch_size = params.batch_size

    # number of loop iterations
    params.iter_per_epoch = (num_examples // batch_size)
    num_iter = params.iter_per_epoch * params.end_epoch
    params.num_iter = num_iter
    ls = params.cnn_fan if params.cnn else params.encoder_layers

    join, split_lu, labeled, unlabeled = get_batch_ops(batch_size)

    # -----------------------------
    # Placeholders
    inputs_placeholder = tf.placeholder(tf.float32, shape=(None, ls[0]))
    inputs = preprocess(inputs_placeholder, params)
    outputs = tf.placeholder(tf.float32)
    train_flag = tf.placeholder(tf.bool)

    # -----------------------------
    # Batch norm
    if params.bn_decay == 'dynamic':
        bn_decay = tf.Variable(1e-10, trainable=False)
    else:
        bn_decay = 0.99
    bn = BatchNormLayers(ls, bn_decay=bn_decay)

    # -----------------------------
    print("=== Corrupted Encoder === ")
    corr = Encoder(inputs=inputs, encoder_layers=ls, bn=bn,
                        is_training=train_flag,
                        noise_sd=params.encoder_noise_sd, start_layer=0,
                        batch_size=params.batch_size, update_batch_stats=False,
                        scope='enc', reuse=None)

    # -----------------------------
    print("=== Clean Encoder ===")
    clean = Encoder(inputs=inputs, encoder_layers=ls, bn=bn,
                        is_training=train_flag, noise_sd=0.0, start_layer=0,
                        batch_size=params.batch_size, update_batch_stats=True,
                        scope='enc', reuse=True)
    # -----------------------------
    print("=== Decoder ===")
    # if params.combinator == 'amlp':
    #     Cmb = Combinator
    # elif params.combinator == 'mlp':
    #     Cmb = MLPCombinator
    # else:
    #     Cmb = GaussCombinator
    # -----------------------------
    dec = Decoder(clean=clean, corr=corr, bn=bn,
                      combinator=gauss_combinator,
                      encoder_layers=params.encoder_layers,
                      denoising_cost=params.rc_weights,
                      batch_size=params.batch_size,
                      scope='dec', reuse=None)

    # -----------------------------
    # Metrics
    # -----------------------------
    # Calculate total unsupervised cost
    u_cost = tf.add_n(dec.d_cost)
    ce = tf.nn.softmax_cross_entropy_with_logits(
                labels=outputs, logits=labeled(corr.logits))
    cost = tf.reduce_mean(ce)

    loss = cost + u_cost

    # no of correct predictions
    correct_prediction = tf.equal(tf.argmax(clean.logits, 1), tf.argmax(outputs, 1))

    accuracy = tf.reduce_mean(
        tf.cast(correct_prediction, "float")) * tf.constant(100.0)

    # -----------------------------
    # Training operations
    # -----------------------------
    learning_rate = tf.Variable(starter_learning_rate, trainable=False)
    train_step = tf.train.AdamOptimizer(learning_rate).minimize(loss)

    # add the updates of batch normalization statistics to train_step
    bn_updates = tf.group(*bn.bn_assigns)
    with tf.control_dependencies([train_step]):
        train_step = tf.group(bn_updates)

    saver = tf.train.Saver(keep_checkpoint_every_n_hours=0.5, max_to_keep=5)

    # -----------------------------
    # This needs to run after the graph is built to correctly count the
    # number of trainable parameters
    # Write logs to appropriate directory
    log_dir = params.logdir + params.id
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    desc_file = log_dir + "/" + "description"
    with open(desc_file, 'a') as f:
        print(*order_param_settings(params), sep='\n', file=f, flush=True)
        print("Trainable parameters:", count_trainable_params(), file=f,
              flush=True)

    log_file = log_dir + "/" + "train_log"

    # -----------------------------
    print("===  Starting Session ===")
    sess = tf.Session()
    i_iter = 0
    # -----------------------------
    # Resume from checkpoint
    ckpt_dir = "checkpoints/" + params.id + "/"
    ckpt = tf.train.get_checkpoint_state(
        ckpt_dir)  # get latest checkpoint (if any)
    if ckpt and ckpt.model_checkpoint_path:
        # if checkpoint exists, restore the parameters and set epoch_n and i_iter
        saver.restore(sess, ckpt.model_checkpoint_path)
        epoch_n = int(ckpt.model_checkpoint_path.split('/')[-1].split('-')[1])
        i_iter = (epoch_n + 1) * (num_examples // batch_size)
        print("Restored Epoch ", epoch_n)
    else:
        # no checkpoint exists. create checkpoints directory if it does not exist.
        if not os.path.exists(ckpt_dir):
            os.makedirs(ckpt_dir)
        init = tf.global_variables_initializer()
        sess.run(init)


    # -----------------------------
    print("=== Training ===")

    def evaluate_metric(dataset, sess, op):
        metric = 0
        num_eval_iters = dataset.num_examples // batch_size
        for _ in range(num_eval_iters):
            images, labels = dataset.next_batch(batch_size)
            init_feed = {inputs_placeholder: images,
                         outputs: labels,
                         train_flag: False}
            metric += sess.run(op, init_feed)
        metric /= num_eval_iters
        return metric

    def evaluate_metric_list(dataset, sess, ops):
        metrics = [0.0 for _ in ops]
        num_eval_iters = dataset.num_examples // batch_size
        for _ in range(num_eval_iters):
            images, labels = dataset.next_batch(batch_size)
            init_feed = {inputs_placeholder: images,
                         outputs: labels,
                         train_flag: False}
            op_eval = sess.run(ops, init_feed)

            for i, op in enumerate(op_eval):
                metrics[i] += op

        metrics = [metric/num_eval_iters for metric in metrics]
        return metrics

    # -----------------------------
    # Evaluate initial training accuracy and losses
    # init_loss = evaluate_metric(
        # mnist.train.labeled_ds, sess, cost)
    with open(desc_file, 'a') as f:
        print('================================', file=f, flush=True)
        print("Initial Train Accuracy: ",
              sess.run(accuracy, feed_dict={
                  inputs_placeholder: mnist.train.labeled_ds.images,
                  outputs: mnist.train.labeled_ds.labels,
                  train_flag: False}),
              "%", file=f, flush=True)
        print("Initial Train Losses: ", *evaluate_metric_list(mnist.train, sess, [loss, cost, u_cost]), file=f, flush=True)

        # -----------------------------
        # Evaluate initial testing accuracy and cross-entropy loss
        print("Initial Test Accuracy: ",
              sess.run(accuracy, feed_dict={
                  inputs_placeholder: mnist.test.images,
                  outputs: mnist.test.labels,
                  train_flag: False}),
              "%", file=f, flush=True)
        print("Initial Test Cross Entropy: ",
              evaluate_metric(mnist.test, sess, cost), file=f, flush=True)

    start = time.time()
    for i in tqdm(range(i_iter, num_iter)):

        images, labels = mnist.train.next_batch(batch_size)

        _ = sess.run(
            [train_step],
            feed_dict={inputs_placeholder: images,
                       outputs: labels,
                       train_flag: True})

        if (i > 1) and ((i + 1) % (params.test_frequency_in_epochs * (
                    num_iter // params.end_epoch)) == 0):

            now = time.time() - start
            epoch_n = i // (num_examples // batch_size)

            if (epoch_n + 1) >= decay_after:
                # epoch_n + 1 because learning rate is set for next epoch
                ratio = 1.0 * (params.end_epoch - (epoch_n + 1))
                ratio = max(0., ratio / (params.end_epoch - decay_after))
                sess.run(learning_rate.assign(starter_learning_rate * ratio))

            if not params.do_not_save:
                saver.save(sess, ckpt_dir + 'model.ckpt', epoch_n)

            # ---------------------------------------------
            # Compute error on testing set (10k examples)
            test_cost = evaluate_metric(mnist.test, sess, cost)

            # Create log of:
            # time, epoch number, test accuracy, test cross entropy,
            # train accuracy, train loss, train cross entropy,
            # train reconstruction loss

            log_i = [now, epoch_n] + sess.run(
                [accuracy],
                feed_dict={inputs_placeholder: mnist.test.images,
                           outputs: mnist.test.labels,
                           train_flag: False}
            ) + [test_cost] + sess.run(
                [accuracy],
                feed_dict={inputs_placeholder:
                               mnist.train.labeled_ds.images,
                           outputs: mnist.train.labeled_ds.labels,
                           train_flag: False}
            ) + sess.run(
                [loss, cost, u_cost],
                feed_dict={inputs_placeholder: images,
                           outputs: labels,
                           train_flag: False})

            with open(log_file, 'a') as train_log:
                print(*log_i, sep=',', flush=True, file=train_log)

    with open(desc_file, 'a') as f:
        print("Final Accuracy: ", sess.run(accuracy, feed_dict={
            inputs_placeholder: mnist.test.images, outputs: mnist.test.labels,
            train_flag: False}),
              "%", file=f, flush=True)


    sess.close()


if __name__ == '__main__':
    main()







