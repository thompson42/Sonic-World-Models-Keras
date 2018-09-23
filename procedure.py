'''
Dossiers du projet :

|__ data
	|__ actions
	|__ images
	|__ latent_images
	|__ reconstructed_images
|__ models
|__ saved_models

'''
from keras.engine.saving import load_model
from data_generation import generate_data
from models.LSTM import LSTM
import numpy as np
from constants import *
from models.MDN_LSTM import MDN_LSTM
from models.VAE import VAE
from play import play
from process import create_project_folders


create_project_folders()

'''
	===============================================
	0 - Juste pour jouer au jeu :D
	===============================================
'''

# print('Entraînez-vous à jouer !')
# play(game='SonicTheHedgehog-Genesis', state='GreenHillZone.Act1')

'''
	===============================================
	1 - Création des données d'entrainement pour le VAE
	===============================================
'''

# print('\nGénération données VAE.')
# Faire ~5 enregistrements (chacun suivi d'un reset du niveau avec "BACKSPACE")
# generate_data(game='SonicTheHedgehog-Genesis', state='GreenHillZone.Act1', extension_name=VAE_TRAINING_EXT, frame_jump=4, save_actions=False)

'''
	===============================================
	2 - Entraînement du VAE
	===============================================
'''

# print('\nEntraînement VAE.')
vae = VAE()
# /!\ batch_size=32 (voir 64 ou 128) est un bon choix si la mémoire de votre carte graphique le permet, sinon choisir plus petit
# vae.train(batch_size=32, epochs=100)
# vae.save_weights(SAVED_MODELS_DIR + '/VAE.h5')
vae.load_weights(file_path=SAVED_MODELS_DIR + '/VAE.h5')

'''
	===============================================
	3 - Visualisation du VAE en action
	===============================================
'''

# print('Visualisation VAE')
# images_array_path = IMG_DIR + '/GreenHillZone.Act1.vae_train1.npy'
# vae.generate_render(data_path=images_array_path)

'''
	===============================================
	4 - Génération des données d'entraînement du LSTM
	Cet entraînement à pour but de faire apprendre au LSTM la logique/physique du jeu afin qu'il puisse prédire les
	prochaines frames, il faut donc créer un dataset d'entraînement de qualité, c-à-d avec la plus grande variété de
	situations possible (exemple : ne pas bouger -> le décors ne bouge plus ; bloquer contre un mur -> plus rien n'avance...)
	===============================================
'''

# print('\nGénération données LSTM.')

# Faire une dizaine d'enregistrements (5 si 8Go de RAM)
# print("\tDonnées d'entraînement")
# generate_data(game='SonicTheHedgehog-Genesis', state='GreenHillZone.Act1', extension_name=RNN_TRAINING_EXT, frame_jump=FRAME_JUMP, fixed_record_size=True)
# Faire 2 enregistrement (1 si 8Go de RAM)
# print("\tDonnées de validation")
# generate_data(game='SonicTheHedgehog-Genesis', state='GreenHillZone.Act1', extension_name=RNN_TEST_EXT, frame_jump=FRAME_JUMP, fixed_record_size=True)

X_train_rnn, Y_train_rnn, X_test_rnn, Y_test_rnn = vae.generate_latent_images()
random_latent_image = Y_train_rnn[42]
X_train_rnn = np.reshape(X_train_rnn, (X_train_rnn.shape[0], 1, X_train_rnn.shape[1]))
X_test_rnn = np.reshape(X_test_rnn, (X_test_rnn.shape[0], 1, X_test_rnn.shape[1]))

'''
	===============================================
	5 - Entraînement du LSTM
	===============================================
'''

print('\nEntraînement LSTM.')

lstm = LSTM()
# lstm.train(X_train=X_train_rnn, Y_train=Y_train_rnn, validation_data=(X_test_rnn, Y_test_rnn), epochs=200)
# lstm.save_weights(SAVED_MODELS_DIR + '/LSTM.h5')
lstm.load_weights(SAVED_MODELS_DIR + '/LSTM.h5')

'''
	===============================================
	5 - Variante - Entraînement du MDN_LSTM
	===============================================
'''

# TODO : ne fonctionne plus, à régler, erreur non-explicite
# print('\nEntraînement MDN_LSTM.')

# mdn_lstm = MDN_LSTM()
# mdn_lstm.train(X_train=X_train_rnn, Y_train=Y_train_rnn, val_data=(X_test_rnn, Y_test_rnn), epochs=200)
# mdn_lstm.save_weights(SAVED_MODELS_DIR + '/MDN_LSTM.h5')
# mdn_lstm.load_weights(SAVED_MODELS_DIR + '/MDN_LSTM.h5')

'''
	===============================================
	6 - Jouer à sonic dans le LSTM entraîné
	===============================================
'''

del X_train_rnn, X_test_rnn, Y_train_rnn, Y_test_rnn
print('\nJouez dans un niveau rêvé par le LSTM !')

# Le LSTM commence à partir d'une image latente choisie arbitrairement
# On peut choisir un autre indice afin que le "rêve" du LSTM démarre différemment
latent_image = [random_latent_image]
# Choisir entre "lstm" et "mdn_lstm" suivant le choix en 5)
lstm.play_in_dream(start_image=latent_image, decoder=vae.decoder)
