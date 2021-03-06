"""Main DQN agent."""
import numpy as np
from gym import wrappers

class DQNAgent:
    """Class implementing DQN.

    This is a basic outline of the functions/parameters you will need
    in order to implement the DQNAgnet. This is just to get you
    started. You may need to tweak the parameters, add new ones, etc.

    Feel free to change the functions and funciton parameters that the
    class provides.

    We have provided docstrings to go along with our suggested API.

    Parameters
    ----------
    q_network: keras.models.Model
      Your Q-network model.
    preprocessor: deeprl_hw2.core.Preprocessor
      The preprocessor class. See the associated classes for more
      details.
    memory: deeprl_hw2.core.Memory
      Your replay memory.
    gamma: float
      Discount factor.
    target_update_freq: float
      Frequency to update the target network. You can either provide a
      number representing a soft target update (see utils.py) or a
      hard target update (see utils.py and Atari paper.)
    num_burn_in: int
      Before you begin updating the Q-network your replay memory has
      to be filled up with some number of samples. This number says
      how many.
    train_freq: int
      How often you actually update your Q-Network. Sometimes
      stability is improved if you collect a couple samples for your
      replay memory, for every Q-network update that you run.
    batch_size: int
      How many samples in each minibatch.
    """
    def __init__(self,
                 q_network,
                 preprocessor,
                 memory,
                 policy,
                 gamma,
                 target_update_freq,
                 num_burn_in,
                 train_freq,
                 batch_size):
        self.model = q_network
        self.preprocessor = preprocessor
        self.memory = memory
        self.policy = policy
        self.gamma = gamma
        self.target_update_freq = target_update_freq
        self.num_burn_in = num_burn_in
        self.train_freq = train_freq
        self.batch_size = batch_size


    def compile(self, optimizer, loss_func):
        """Setup all of the TF graph variables/ops.

        This is inspired by the compile method on the
        keras.models.Model class.

        This is a good place to create the target network, setup your
        loss function and any placeholders you might need.
        
        You should use the mean_huber_loss function as your
        loss_function. You can also experiment with MSE and other
        losses.

        The optimizer can be whatever class you want. We used the
        keras.optimizers.Optimizer class. Specifically the Adam
        optimizer.
        """
        self.model.compile(optimizer=optimizer, loss=loss_func)

    def calc_q_values(self, state):
        """Given a state (or batch of states) calculate the Q-values.

        Basically run your network on these states.

        Return
        ------
        Q-values for the state(s)
        """
        q_values = self.model.predict_on_batch(np.expand_dims(state, axis=0))
        #print('q_values:{0}'.format(q_values[0]))
        return q_values


    def select_action(self, q_values, **kwargs):
        """Select the action based on the current state.

        You will probably want to vary your behavior here based on
        which stage of training your in. For example, if you're still
        collecting random samples you might want to use a
        UniformRandomPolicy.

        If you're testing, you might want to use a GreedyEpsilonPolicy
        with a low epsilon.

        If you're training, you might want to use the
        LinearDecayGreedyEpsilonPolicy.

        This would also be a good place to call
        process_state_for_network in your preprocessor.

        Returns
        --------
        selected action
        """

        return self.policy.select_action(q_values)


    def update_policy(self):
        """Update your policy.

        Behavior may differ based on what stage of training your
        in. If you're in training mode then you should check if you
        should update your network parameters based on the current
        step and the value you set for train_freq.

        Inside, you'll want to sample a minibatch, calculate the
        target values, update your network, and then update your
        target values.

        You might want to return the loss and other metrics as an
        output. They can help you monitor how training is going.
        """
        pass

    def fit(self, env, num_iterations, max_episode_length=None):
        """Fit your model to the provided environment.

        Its a good idea to print out things like loss, average reward,
        Q-values, etc to see if your agent is actually improving.

        You should probably also periodically save your network
        weights and any other useful info.

        This is where you should sample actions from your network,
        collect experience samples and add them to your replay memory,
        and update your network parameters.

        Parameters
        ----------
        env: gym.Env
          This is your Atari environment.
        num_iterations: int
          How many samples/updates to perform.
        max_episode_length: int
          How long a single episode should last before the agent
          resets. Can help exploration.
        """
        state = env.reset()
        iter_epi = 0
        for i in range(num_iterations):
            if iter_epi >= max_episode_length:
                iter_epi = 0
                state = env.reset()
                self.preprocessor.reset()

            processed_state = self.preprocessor.process_state_for_network(state)

            q_values = self.calc_q_values(processed_state)
            action = self.select_action(q_values)

            next_state, reward, is_terminal, debug_info = env.step(action)
            if is_terminal:
                state = env.reset()
                iter_epi = 0
                self.preprocessor.reset()
                continue

            env.render()
            # todo put into memory
            processed_next_state = self.preprocessor.process_state_for_network(next_state)
            next_q_value = self.calc_q_values(processed_next_state)

            #target: only different at chosen action
            target = reward + self.gamma * max(next_q_value[0])
            q_values_target = q_values
            q_values_target[0, action] = target

            loss = self.model.train_on_batch(np.expand_dims(processed_state, axis=0), np.expand_dims(target, axis=0))
            if i%10 == 0:
                print('iter= {0}, loss = {1}'.format(i, loss))
                print('q_value: {0}'.format(q_values))
            state = next_state
            iter_epi += 1


    def evaluate(self, env, num_episodes, max_episode_length=None):
        """Test your agent with a provided environment.
        
        You shouldn't update your network parameters here. Also if you
        have any layers that vary in behavior between train/test time
        (such as dropout or batch norm), you should set them to test.

        Basically run your policy on the environment and collect stats
        like cumulative reward, average episode length, etc.

        You can also call the render function here if you want to
        visually inspect your policy.
        """
        env = wrappers.Monitor(env, self.)
        total_reward = 0
        for i in range(num_episodes):
            state = env.reset()
            is_terminal = 0
            while not is_terminal:
                processed_state = self.preprocessor.process_state_for_network(state)
                q_values = self.calc_q_values(processed_state)
                action = self.select_action(q_values)
                next_state, reward, is_terminal, debug_info = env.step(action)
                total_reward += reward
                state = next_state
                env.render()
        average_reward = total_reward / num_episodes
