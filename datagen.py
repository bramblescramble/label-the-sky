from albumentations import Compose, Flip, HorizontalFlip, RandomRotate90, ShiftScaleRotate
from cv2 import imread
import numpy as np
from keras.utils import Sequence
import os


class DataGenerator(Sequence):
    # adapted from https://stanford.edu/~shervine/blog/keras-how-to-generate-data-on-the-fly
    def __init__(
        self, object_ids, data_folder, input_dim, target='classes', labels=None, 
        batch_size=32, n_outputs=3, shuffle=True, extension='npy', augmentation=True):
        self.batch_size = batch_size
        self.data_folder = data_folder
        self.labels = labels
        self.n_outputs = n_outputs
        self.object_ids = object_ids
        self.shape = input_dim
        self.shuffle = shuffle
        self.target = target

        self.augmentation = augmentation
        self.bands = [0, 5, 7, 9, 11] if self.shape[2]==5 else None
        self.aug = self.compose_augment()
        self.extension = '.npy' if self.shape[2]>3 else '.png'
        self.shape_orig = self.shape[:-1] + (12,)

        self.on_epoch_end()


    def __len__(self):
        # define the number of batches per epoch
        return np.maximum(len(self.object_ids) // self.batch_size, 1)


    def __getitem__(self, index):
        # generate indexes of one data batch
        indexes = self.indexes[index*self.batch_size:(index+1)*self.batch_size]
        list_ids_temp = [self.object_ids[k] for k in indexes]
        X, y = self.__data_generation(list_ids_temp)
        # X = np.float32(X)

        if self.target=='autoencoder':
            return X, X

        if y is None:
            return X

        return X, y


    def on_epoch_end(self):
        # update indexes after each epoch
        self.indexes = np.arange(len(self.object_ids))
        if self.shuffle == True:
            np.random.shuffle(self.indexes)


    def compose_augment(self, p=.9):
        return Compose([
            Flip(),
            HorizontalFlip(),
            # ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.1, rotate_limit=45, p=.5),
        ], p=p)


    def augment(self, image):
        return self.aug(image=image)['image']


    def __data_generation(self, list_ids_temp):
        # generate data containing batch_size samples
        X = np.empty((self.batch_size,)+self.shape)
        y = np.zeros((self.batch_size, self.n_outputs), dtype=np.float32)

        for i, object_id in enumerate(list_ids_temp):
            filepath = os.path.join(self.data_folder, object_id.split('.')[0], object_id+self.extension)

            if self.extension == '.png':
                im = imread(filepath)
            else:
                if self.bands is not None:
                    im = np.load(filepath).reshape(self.shape_orig)
                    im = im[:,:,self.bands]
                else:
                    im = np.load(filepath).reshape(self.shape)

            if self.augmentation:
                im = self.augment(im)
            X[i,:] = im

            if self.labels is not None:
                y[i,:] = self.labels[object_id]

        if self.labels is None:
            return X, None

        return X, y