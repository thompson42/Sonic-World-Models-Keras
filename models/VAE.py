from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.layers import Dense, Input, Conv2D, Flatten, Lambda, Reshape, Conv2DTranspose, BatchNormalization as BN, \
	Dropout, MaxPooling2D, ReLU, LeakyReLU
from keras.models import Model
from keras.losses import binary_crossentropy
from keras import backend as K
from constants import *
import numpy as np
import os
import glob
import matplotlib.pyplot as plt


def sampling(args):
	z_mean, z_log_var = args
	epsilon = K.random_normal(shape=(K.shape(z_mean)[0], LATENT_DIM), mean=0.0, stddev=1.0)
	return z_mean + K.exp(0.5 * z_log_var) * epsilon


class VAE():
	def __init__(self):
		self.models = self._build()
		self.vae = self.models[0]
		self.encoder = self.models[1]
		self.decoder = self.models[2]

	def _build(self):
		inputs = Input(shape=IMG_SHAPE, name='encoder_input')
		# Size of the image given in input : (224, 320, 3)
		x = Conv2D(filters=32, kernel_size=3, strides=2, kernel_initializer='normal', padding='same')(inputs)
		x = LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		# (112, 160, 32)
		x = Conv2D(filters=64, kernel_size=3, strides=2, kernel_initializer='normal', padding='same')(x)
		x =LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		# (56 80, 64)
		x = Conv2D(filters=128, kernel_size=3, strides=2, kernel_initializer='normal', padding='same')(x)
		x =LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		# (28, 40, 128)
		x = Conv2D(filters=256, kernel_size=3, strides=2, kernel_initializer='normal', padding='same')(x)
		x =LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		# (14, 20, 128)
		x = Conv2D(filters=256, kernel_size=3, strides=2, kernel_initializer='normal', padding='same')(x)
		x =LeakyReLU()(x)
		# x = Dropout(0.5)(x)
		x = BN()(x)
		# (7, 10, 128)
		# We save the shape for the decoder part
		shape = K.int_shape(x)

		# generate latent vector Q(z|X)
		x = Flatten()(x)
		x = Dense(1024)(x)
		x =LeakyReLU()(x)
		# x = Dropout(0.5)(x)
		x = BN()(x)
		z_mean = Dense(LATENT_DIM, name='z_mean')(x)
		z_mean =LeakyReLU()(z_mean)
		z_mean = BN()(z_mean)
		z_log_var = Dense(LATENT_DIM, name='z_log_var', activation='tanh')(x)
		z_log_var = BN()(z_log_var)

		# use reparameterization trick to push the sampling out as input
		# note that "output_shape" isn't necessary with the TensorFlow backend
		z = Lambda(sampling, output_shape=(LATENT_DIM,), name='z')([z_mean, z_log_var])

		# instantiate encoder model
		encoder = Model(inputs, z, name='encoder')
		# encoder.summary()

		# build decoder model
		latent_inputs = Input(shape=(LATENT_DIM,), name='z_sampling')
		x = Dense(shape[1] * shape[2] * shape[3])(latent_inputs)
		x =LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		x = Reshape((shape[1], shape[2], shape[3]))(x)

		x = Conv2DTranspose(filters=256, kernel_size=4, strides=2, kernel_initializer='normal', padding='same')(x)
		x =LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		# (14, 20, 128)
		x = Conv2DTranspose(filters=128, kernel_size=4, strides=2, kernel_initializer='normal', padding='same')(x)
		x =LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		# (28, 40, 64)
		x = Conv2DTranspose(filters=64, kernel_size=4, strides=2, kernel_initializer='normal', padding='same')(x)
		x = LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		# (56, 80, 64)
		x = Conv2DTranspose(filters=32, kernel_size=4, strides=2, kernel_initializer='normal', padding='same')(x)
		x =LeakyReLU()(x)
		# x = Dropout(0.25)(x)
		x = BN()(x)
		# (112, 160, 64)
		x = Conv2DTranspose(filters=3, kernel_size=4, strides=2, kernel_initializer='normal', padding='same',
								  activation='sigmoid')(x)
		outputs = BN()(x)
		# (224, 320, 3)
		# instantiate decoder model
		decoder = Model(latent_inputs, outputs, name='decoder')
		# decoder.summary()

		# instantiate VAE model
		outputs = decoder(encoder(inputs))
		vae = Model(inputs, outputs, name='vae')

		# A classical loss function that uses binary crossentropy
		reconstruction_loss = IMG_SHAPE[0] * IMG_SHAPE[1] * IMG_SHAPE[2] * binary_crossentropy(K.flatten(inputs),
																							   K.flatten(outputs))

		# Custom cost function
		kl_loss = -0.5 * K.sum(1 + z_log_var - K.square(z_mean) - K.exp(z_log_var), axis=-1)

		# The model's cost function is a combination of the binary_crossentropy and the custom loss function
		vae_loss = K.mean(reconstruction_loss + kl_loss)
		vae.add_loss(vae_loss)
		vae.compile(optimizer='adam')

		return (vae, encoder, decoder)

	def save_weights(self, file_path):
		self.vae.save_weights(filepath=file_path)

	def load_weights(self, file_path):
		self.vae.load_weights(filepath=file_path)

	def train(self, filepath, epochs=100, batch_size=32, validation_split=0.2):
		training_data = None

		# We load all the numpy arrays created by the user for the VAE
		for data_file in glob.glob(os.path.join(IMG_DIR, '*' + VAE_TRAINING_EXT + '*.npy')):
			print(data_file)
			if training_data is None:
				training_data = np.load(data_file)
			else:
				training_data = np.concatenate((training_data, np.load(data_file)))

		# Loaded array is of uint8 type, dividing it by 255 automatically converts it into float64 type.
		# For memory purposes, I convert switch to float16 type.
		training_data = training_data.astype(np.float16) / 255

		# If the network didn't improve during the last 5 epochs, we stop the training.
		earlyStop = EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=6, verbose=2)
		checkpoint = ModelCheckpoint(filepath, monitor='val_loss', verbose=2, save_best_only=True, mode='min')
		callbacks_list = [earlyStop, checkpoint]

		self.vae.fit(training_data, epochs=epochs, batch_size=batch_size, verbose=2, callbacks=callbacks_list,
					 validation_split=validation_split, shuffle=True)

	def generate_latent_images(self):

		# ================ training data =====================

		training_latent_images = None
		for data_file in glob.glob(os.path.join(IMG_DIR, '*' + RNN_TRAINING_EXT + '*.npy')):
			print(data_file)
			if training_latent_images is None:
				training_latent_images = np.load(data_file).astype(np.float16) / 255
			else:
				training_latent_images = np.concatenate((training_latent_images, np.load(data_file).astype(np.float16)/255))
		training_latent_images = self.encoder.predict(training_latent_images)

		training_actions = None
		for data_file in glob.glob(os.path.join(ACTIONS_DIR, '*' + RNN_TRAINING_EXT + '*.npy')):
			print(data_file)
			if training_actions is None:
				training_actions = np.load(data_file)
			else:
				training_actions = np.concatenate((training_actions, np.load(data_file)))

		x_train = np.append(training_latent_images, training_actions, axis=1)
		y_train = training_latent_images

		del training_latent_images, training_actions
		x_train = np.delete(x_train[:np.shape(x_train)[0] - 1], np.s_[SEQ_LENGTH::SEQ_LENGTH + 1], axis=0)
		y_train = np.delete(y_train, np.s_[::SEQ_LENGTH + 1], axis=0)

		# ================ validation data =====================

		validation_latent_images = None
		for data_file in glob.glob(os.path.join(IMG_DIR, '*' + RNN_TEST_EXT + '*.npy')):
			print(data_file)
			if validation_latent_images is None:
				validation_latent_images = np.load(data_file).astype(np.float16)/255
			else:
				validation_latent_images = np.concatenate((validation_latent_images, np.load(data_file).astype(np.float16)/255))
		validation_latent_images = self.encoder.predict(validation_latent_images)

		validation_actions = None
		for data_file in glob.glob(os.path.join(ACTIONS_DIR, '*' + RNN_TEST_EXT + '*.npy')):
			print(data_file)
			if validation_actions is None:
				validation_actions = np.load(data_file)
			else:
				validation_actions = np.concatenate((validation_actions, np.load(data_file)))

		x_test = np.append(validation_latent_images, validation_actions, axis=1)
		y_test = validation_latent_images
		del validation_latent_images, validation_actions
		x_test = np.delete(x_test[:np.shape(x_test)[0] - 1], np.s_[SEQ_LENGTH::SEQ_LENGTH + 1], axis=0)
		y_test = np.delete(y_test, np.s_[::SEQ_LENGTH + 1], axis=0)

		return x_train, y_train, x_test, y_test

	def generate_render(self, data_path, save_path=None):
		'''
		Display the render of the VAE given a dataset of images.

		:param data_path: path of the images for the VAE encoding/decoding
		:param save_path: If not None, we save the VAE's images
		:return:
		'''
		images = np.load(data_path).astype(np.float16)
		images = images / 255

		generated_images = []
		for image in images:
			img = np.reshape(image, (1, 224, 320, 3))
			img = self.vae.predict(img)
			img = img.reshape(IMG_SHAPE)
			if (save_path != None):
				generated_images.append(img)
			plt.clf()
			plt.imshow(img, vmin=0, vmax=1)
			plt.pause(0.0000001)
		if (save_path != None):
			np.save(save_path, generated_images)
