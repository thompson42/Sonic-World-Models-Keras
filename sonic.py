# Evolve a control/reward estimation network for the OpenAI Gym
# LunarLander-v2 environment (https://gym.openai.com/envs/LunarLander-v2).
# Sample run here: https://gym.openai.com/evaluations/eval_FbKq5MxAS9GlvB7W6ioJkg
# NOTE: This was run using revision 1186029827c156e0ff6f9b36d6847eb2aa56757a of CodeReclaimers/neat-python, not a release on PyPI.
import gym
import matplotlib.pyplot as plt
import multiprocessing
import neat
import numpy as np
import os
import pickle
import time
import visualize
from models.VAE import VAE
from constants import *
import retro

env = retro.make(game='SonicTheHedgehog-Genesis', state='GreenHillZone.Act1', use_restricted_actions=retro.ACTIONS_ALL,
				 scenario='scenario')

# env = gym.wrappers.Monitor(env, 'results', force=True)

MIN_REWARD = 0
MAX_REWARD = 9000
MAX_STEPS_WITHOUT_PROGRESS = 600
MAX_STEPS = 4500

score_range = []

vae = VAE()
vae.load_weights(file_path=SAVED_MODELS_DIR + '/VAE.h5')
encoder = vae.encoder


class PooledErrorCompute(object):
	def __init__(self):
		self.pool = multiprocessing.Pool()

	def evaluate_genomes(self, genomes, config):
		t0 = time.time()
		nets = []
		for gid, g in genomes:
			nets.append((g, neat.nn.FeedForwardNetwork.create(g, config)))
			g.fitness = []

		print("network creation time {0}".format(time.time() - t0))
		t0 = time.time()

		episodes_score = []
		for genome, net in nets:
			observation = env.reset()
			observation = np.reshape(observation, (1, observation.shape[0], observation.shape[1], observation.shape[2]))
			latent_vector = encoder.predict(observation)[0]
			step = 0
			best_score_step = 0
			total_score = 0.0
			best_score = 0.0
			steps_without_progress = 0

			while 1:
				# Le jeu est en 60 fps : on ne fait jouer l'IA qu'en 15 fps (toutes les 4 frames)
				# S'il s'agit d'une des trois frames où l'IA ne joue pas, elle répète tout simplement sa dernière action
				if step % 4 == 0:
					action = np.zeros((12,), dtype=np.bool)
					if net is not None:
						output = net.activate(latent_vector)
						bool_output = []
						for value in output:
							if value <= 0:
								bool_output.append(False)
							else:
								bool_output.append(True)
						action = np.zeros((12,), dtype=np.bool)
						action[1] = bool_output[Actions.JUMP]
						action[6] = bool_output[Actions.LEFT]
						action[7] = bool_output[Actions.RIGHT]
						action[5] = bool_output[Actions.DOWN]
					last_action = action
				else:
					action = last_action
				observation, reward, done, info = env.step(action)
				observation = np.reshape(observation, (1, observation.shape[0], observation.shape[1], observation.shape[2]))
				latent_vector = encoder.predict(observation)[0]
				del observation
				total_score += reward
				if total_score > best_score:
					best_score = total_score
					best_score_step = step
					steps_without_progress = 0
				else:
					steps_without_progress += 1

				if done or step >= MAX_STEPS or steps_without_progress >= MAX_STEPS_WITHOUT_PROGRESS:
					break

				step += 1

			episodes_score.append(total_score)
			genome.fitness = total_score - best_score_step

		print("simulation run time {0}".format(time.time() - t0))

		scores = [s for s in episodes_score]
		score_range.append((min(scores), np.mean(scores), max(scores)))
		print('best score : ' + max(scores))


def run():
	# Load the config file, which is assumed to live in
	# the same directory as this script.
	local_dir = os.path.dirname(__file__)
	config_path = os.path.join(local_dir, 'config')
	config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
						 neat.DefaultSpeciesSet, neat.DefaultStagnation,
						 config_path)

	# Create the population, which is the top-level object for a NEAT run.
	pop = neat.Population(config)
	stats = neat.StatisticsReporter()
	pop.add_reporter(stats)
	# Add a stdout reporter to show progress in the terminal.
	pop.add_reporter(neat.StdOutReporter(True))
	# Checkpoint every 10 generations or 900 seconds.
	pop.add_reporter(neat.Checkpointer(10, 900))

	# Run until the winner from a generation is able to solve the environment
	# or the user interrupts the process.
	ec = PooledErrorCompute()
	while 1:
		try:
			pop.run(ec.evaluate_genomes, 1)

			visualize.plot_stats(stats, ylog=False, view=False, filename="fitness.svg")

			if score_range:
				S = np.array(score_range).T
				plt.plot(S[0], 'r-')
				plt.plot(S[1], 'b-')
				plt.plot(S[2], 'g-')
				plt.grid()
				plt.savefig("score-ranges.svg")
				plt.close()

			mfs = sum(stats.get_fitness_mean()[-5:]) / 5.0
			print("Average mean fitness over last 5 generations: {0}".format(mfs))

			mfs = sum(stats.get_fitness_stat(min)[-5:]) / 5.0
			print("Average min fitness over last 5 generations: {0}".format(mfs))

			# Use the best genome seen so far as an ensemble-ish control system.
			best_genome = stats.best_unique_genomes(1)[0]
			best_network = neat.nn.FeedForwardNetwork.create(best_genome, config)

			solved = True
			best_scores = []
			for k in range(100):
				observation = env.reset()
				score = 0
				while 1:
					best_action = best_network.activate(observation)
					observation, reward, done, info = env.step(best_action)
					score += reward
					env.render()
					if done:
						break

				best_scores.append(score)
				avg_score = sum(best_scores) / len(best_scores)
				print(k, score, avg_score)
				if avg_score < MAX_REWARD:
					solved = False
					break

			if solved:
				print("Solved.")

				# Save the winners.
				for n, g in best_genome:
					name = 'winner-{0}'.format(n)
					with open(name + '.pickle', 'wb') as f:
						pickle.dump(g, f)

					visualize.draw_net(config, g, view=False, filename=name + "-net.gv")
					visualize.draw_net(config, g, view=False, filename="-net-enabled.gv", show_disabled=False)
					visualize.draw_net(config, g, view=False, filename="-net-enabled-pruned.gv",
									   show_disabled=False, prune_unused=True)

				break
		except KeyboardInterrupt:
			print("User break.")
			break

	env.close()


if __name__ == '__main__':
	run()