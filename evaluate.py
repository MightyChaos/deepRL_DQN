#!/usr/bin/env python
"""Run Atari Environment with DQN."""
import argparse
import os
import random
import gym

import numpy as np
import tensorflow as tf
from keras.layers import (Activation, Convolution2D, Dense, Flatten, Input, Conv2D,
                          Permute, Lambda)
from keras.models import Model
import keras.backend as K
from keras.optimizers import Adam

import deeprl_hw2 as tfrl
from deeprl_hw2.dqn_replay import DQNAgent
from deeprl_hw2.objectives import mean_huber_loss
from deeprl_hw2.preprocessors import *
from deeprl_hw2.policy import *
from deeprl_hw2.simple_memory import SimpleReplayMemory


def create_model(window, input_shape, num_actions,
                 model_name='q_network'):  # noqa: D103
    """Create the Q-network model.
    Use Keras to construct a keras.models.Model instance (you can also
    use the SequentialModel class).
    We highly recommend that you use tf.name_scope as discussed in
    class when creating the model and the layers. This will make it
    far easier to understnad your network architecture if you are
    logging with tensorboard.
    Parameters
    ----------
    window: int
      Each input to the network is a sequence of frames. This value
      defines how many frames are in the sequence.
    input_shape: tuple(int, int) #84 x 84 greyscale image from preprocessing step
      The expected input image size.
    num_actions: int
      Number of possible actions. Defined by the gym environment.
    model_name: str
      Useful when debugging. Makes the model show up nicer in tensorboard.
    Returns
    -------
    keras.models.Model
      The Q-model.
    """
    input_size = (input_shape[0], input_shape[1], window)
    #input_size = input_shape[0] * input_shape[1] * window
    if model_name == "linear_dqn" or model_name == "linear_ddqn":
        with tf.name_scope(model_name):
            #input = Input(shape=(input_size,), batch_shape=None, name='input')
            input = Input(shape=input_size, batch_shape=None, name='input')
            flat_input = Flatten()(input)
            with tf.name_scope('output'):
                output = Dense(num_actions, activation=None)(flat_input)
    elif model_name == "dqn" or model_name == "ddqn":
        print("create dqn model")
        with tf.name_scope(model_name):
            # input = Input(shape=(input_size,), batch_shape=None, name='input')
            input = Input(shape=input_size, batch_shape=None, name='input')
            conv1 = Conv2D(16, (8, 8), padding='same', strides=(4, 4), activation='relu')(input)
            conv2 = Conv2D(32, (4, 4), padding='same', strides=(2, 2), activation='relu')(conv1)
            flat_conv2 = Flatten()(conv2)
            h3 = Dense(256, activation="relu")(flat_conv2)
            with tf.name_scope('output'):
                output = Dense(num_actions, activation=None)(h3)
    elif model_name == "dueling_dqn":
        print("create dueling dqn model")
        with tf.name_scope(model_name):
            # input = Input(shape=(input_size,), batch_shape=None, name='input')
            input = Input(shape=input_size, batch_shape=None, name='input')
            conv1 = Conv2D(16, (8, 8), padding='same', strides=(4, 4), activation='relu')(input)
            conv2 = Conv2D(32, (4, 4), padding='same', strides=(2, 2), activation='relu')(conv1)
            flat_conv2 = Flatten()(conv2)
            h3 = Dense(256, activation="relu")(flat_conv2)
            with tf.name_scope('q_output'):
                y = Dense(num_actions+1, activation=None)(h3)
            output = Lambda(lambda a: K.expand_dims(a[:, 0], -1) + a[:, 1:] - K.mean(a[:, 1:], keepdims=True),
                                 output_shape=(num_actions,))(y)

    model = Model(inputs=input, outputs=output)
    print(model.summary())

    return model



def get_output_folder(parent_dir, env_name):
    """Return save folder.
    Assumes folders in the parent_dir have suffix -run{run
    number}. Finds the highest run number and sets the output folder
    to that number + 1. This is just convenient so that if you run the
    same script multiple times tensorboard can plot all of the results
    on the same plots with different names.
    Parameters
    ----------
    parent_dir: str
      Path of the directory containing all experiment runs.
    Returns
    -------
    parent_dir/run_dir
      Path to this run's save directory.
    """
    os.makedirs(parent_dir, exist_ok=True)
    experiment_id = 0
    for folder_name in os.listdir(parent_dir):
        if not os.path.isdir(os.path.join(parent_dir, folder_name)):
            continue
        try:
            folder_name = int(folder_name.split('-run')[-1])
            if folder_name > experiment_id:
                experiment_id = folder_name
        except:
            pass
    experiment_id += 1

    parent_dir = os.path.join(parent_dir, env_name)
    parent_dir = parent_dir + '-run{}'.format(experiment_id)
    return parent_dir


def main():  # noqa: D103
    parser = argparse.ArgumentParser(description='Run DQN on given game environment')
    parser.add_argument('--env', default='SpaceInvaders-v0', help='Atari env name')
    # parser.add_argument('--env', default='Pong-v0', help='Atari env name')
    parser.add_argument('--model_name', default="dqn",
                        help='model_name: dqn, ddqn, dueling_dqn')


    parser.add_argument(
        '-o', '--output', default='train', help='Directory to save data to')
    parser.add_argument('--seed', default=0, type=int, help='Random seed')
    parser.add_argument('--gamma', default=0.99, type=float, help='Discount factor')
    parser.add_argument('--target_update_freq', default=10000, type=int, help='interval between two updates of the target network')
    parser.add_argument('--num_burn_in', default=50000, type=int, help='number of samples to be filled into the replay memory before updating the network')
    parser.add_argument('--train_freq', default=1, type=int, help='How often to update the Q-network')
    parser.add_argument('--batch_size', default=32, type=int, help='batch_size')
    parser.add_argument('--num_iterations', default=50000, type=int, help="num of iterations to run for the training")
    parser.add_argument('--max_episode_length', default=1000000, type=int, help='max length of one episode')
    parser.add_argument('--lr', default=0.0001, type=float, help='learning rate')
    parser.add_argument('--epsilon', default=0.05, type=float, help='epsilon for exploration')
    parser.add_argument('--experiment_id', default=None, type=int, help='index of experiment to reload checkpoint')
    parser.add_argument('--save_freq', default=100000, type=int, help='checkpoint saving frequency')
    parser.add_argument('--evaluate_freq', default=10000, type=int, help='frequency to do evaluation and record video by wrapper')
    parser.add_argument('--test_num_episodes', default=100, type=int, help='number of episodes to play at each evaluation')


    parser.add_argument('--memory_size', default=200000, type=int,
                        help='replay memory size')

    parser.add_argument('--z', default=255., type=float,
                        help='normailize constant')

    parser.add_argument('--test_iter', default=100000., type=int,
                        help='iteration number of the to-test trained model')



    args = parser.parse_args()

    if not args.experiment_id:
        args.output = get_output_folder(args.output, args.env)
    else:
        args.output = os.path.join(args.output, args.env) + '-run{}'.format(args.experiment_id)
    game_env = gym.make(args.env)
    num_actions = game_env.action_space.n
    input_shape=(84, 84)

    #todo: setup logger
    #writer = tf.summary.FileWriter()

    #setup model
    model = create_model(window=4, input_shape=input_shape, num_actions=num_actions, model_name=args.model_name)
    model_target = create_model(window=4, input_shape=input_shape, num_actions=num_actions, model_name=args.model_name)

    #setup optimizer
    #optimizer = Adam(lr=args.lr)
    optimizer = tf.train.AdamOptimizer(learning_rate=args.lr)

    #setup preprocessor
    atari_preprocessor = AtariPreprocessor(input_shape)
    history_preprocessor = HistoryPreprocessor(history_length=3)
    preprocessor = PreprocessorSequence([atari_preprocessor, history_preprocessor])
    test_preprocessor = PreprocessorSequence([AtariPreprocessor(input_shape), HistoryPreprocessor(history_length=3)])
    #setup memory
    memory = SimpleReplayMemory(max_size=args.memory_size, window_length=4)
    #setup policy
    # policy = UniformRandomPolicy(num_actions=num_actions)
    # policy = GreedyEpsilonPolicy(epsilon=args.epsilon, num_actions=num_actions)
    policy = LinearDecayGreedyEpsilonPolicy(num_actions=num_actions,
                                            decay=0.9,
                                            start_value=1,
                                            end_value=0.1,
                                            num_steps=1000000)
    #setup DQN agent
    agent = DQNAgent(q_network=model, q_target_network=model_target, preprocessor=preprocessor, test_preprocessor=test_preprocessor,
                     memory=memory, policy=policy, gamma=args.gamma, target_update_freq=args.target_update_freq,
                     num_burn_in=args.num_burn_in, train_freq=args.train_freq, batch_size=args.batch_size, logdir=args.output, save_freq=args.save_freq,
                     evaluate_freq=args.evaluate_freq, test_num_episodes=args.test_num_episodes, env_name=args.env,
                     model_name = args.model_name, z=args.z)
    agent.compile_test_model(args.test_iter)
    average_reward, max_reward, min_reward, std_reward = agent.test_trained_model(num_episodes=args.test_num_episodes, iter=args.test_iter)
    print("average reward: {0}".format(average_reward))
    print("max reward: {0}".format(max_reward))
    print("min reward: {0}".format(min_reward))
    print("std reward: {0}".format(std_reward))
    # here is where you should start up a session,
    # create your DQN agent, create your model, etc.
    # then you can run your fit method.

if __name__ == '__main__':
    main()
