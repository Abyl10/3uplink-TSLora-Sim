import gymnasium as gym
from gymnasium import spaces
import numpy as np
import simpy
from simulator.lora_simulator import LoraSimulator
import simulator.consts as consts
import simulator.utils as utils


class LoRaEnv(gym.Env):
    """
    Custom Environment for LoRa Network Simulation integrated with Reinforcement Learning.
    Follows the gym interface.
    """

    metadata = {"render_modes": ["console"]}

    def __init__(self):
        super(LoRaEnv, self).__init__()

        self.lambda_value = 0.01  # Weight for penalizing retransmissions

        # Actions: number of transmission slots (1, 2, 3)
        self.action_space = spaces.Discrete(3)

        self.nodes_count = 10
        self.data_size = 16
        self.avg_wake_up_time = 30 * 1000
        self.sim_time = 3600 * 1000

        self.observation_space = spaces.Dict(
            {
                "prr": spaces.Box(
                    low=0, high=1, shape=(self.nodes_count,), dtype=np.float64
                ),
                "rssi": spaces.Box(
                    low=-200, high=0, shape=(self.nodes_count,), dtype=np.float64
                ),
                "sf": spaces.Box(
                    low=7, high=9, shape=(self.nodes_count,), dtype=np.int64
                ),
            }
        )

        self.simpy_env = None
        self.simulator = None
        self.current_step = 0
        self.done = False
        self.truncated = False

    def setup(self, nodes_count, data_size, avg_wake_up_time, sim_time):
        self.nodes_count = nodes_count
        self.data_size = data_size
        self.avg_wake_up_time = avg_wake_up_time
        self.sim_time = sim_time

    def _next_observation(self):
        prr = np.array([node.calculate_prr() for node in consts.nodes])
        rssi = np.array([node.rssi_value for node in consts.nodes])
        sf = np.array([node.sf for node in consts.nodes])
        print(
            f"Next Observation for STEP [{self.current_step}]:\nPRR: {prr}\nRSSI: {rssi}\nSF: {sf}\n"
        )
        return {"prr": prr, "rssi": rssi, "sf": sf}

    def step(self, action):
        if self.current_step == 0:
            self.simulator.start_simulation()
        if self.current_step >= (self.sim_time / 1000):
            self.done = True
            reward = self._calculate_reward()
            obs = self._next_observation()
            info = {}
            return obs, reward, self.done, info

        # Update number of transmissions
        self.simulator.update_nodes_behavior(action)

        # Advance the simulation by one second
        self.current_step += 1
        timestep = self.current_step * 1000
        print(f"ACTION TAKEN FOR STEP [{self.current_step}]: {action}")
        self.simulator.env.run(until=timestep)

        reward = self._calculate_reward()
        obs = self._next_observation()
        info = {}

        # Check if the entire simulation duration has been reached
        self.done = self.current_step >= (self.sim_time / 1000)

        return obs, reward, self.done, self.truncated, info

    def _calculate_reward(self):
        return 1

    def reset(self, seed=None, options=None):
        self.simpy_env = simpy.Environment()
        self.current_step = 0
        self.done = False
        self.simulator = LoraSimulator(
            self.nodes_count,
            self.data_size,
            self.avg_wake_up_time,
            self.sim_time,
            self.simpy_env,
        )
        utils.reset_statistics()
        self.simulator.add_nodes()
        info = {}
        return self._next_observation(), info

    def render(self, mode="human"):
        print(self._next_observation())
