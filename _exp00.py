
'''
exp00:

compare raw images (32x32xn features) to catalog (12+1 features)

01. build dataset
02. train log reg
03. predict on validation split
04. compute error
05. plot acc x magnitude curves (save as svg?)

'''

from keras.utils import to_categorical
import os
import numpy as np
import pandas as pd
from skimage import io
from sklearn.linear_model import LogisticRegression
import sys
from time import time


class_map = {'GALAXY': 0, 'STAR': 1, 'QSO': 2}


def build_flattened_dataset(csv_file, input_dir, nbands):
    df_orig = pd.read_csv(csv_file)
    df_orig = df_orig[(df_orig.photoflag==0)&(df_orig.ndet==12)]

    ext = '.png' if nbands==3 else '.npy'
    input_dir = input_dir+'/crops_rgb32' if nbands==3 else input_dir+'/crops_calib'

    X = {}
    y = {}

    start = time()
    for split in ['train', 'val', 'test']:
        print('processing', split)
        df = df_orig[df_orig.split==split]

        y[split] = df['class'].apply(lambda c: class_map[c]).values

        if os.path.exists(os.path.join(os.environ['DATA_PATH'], f'X_flattened_{split}_{nbands}bands.npy')):
            X[split] = np.load(os.path.join(os.environ['DATA_PATH'], f'X_flattened_{split}_{nbands}bands.npy'))
            print(f'loaded: X_flattened_{split}_{nbands}bands.npy')
        else:
            img_list = df.id.values
            img_list = [os.path.join(input_dir, file.split('.')[0], file+ext) for file in img_list]

            if nbands == 3:
                read_func =  io.imread
            else:
                read_func = np.load

            img_shape = read_func(img_list[0]).shape

            X[split] = np.zeros((len(img_list), img_shape[0]*img_shape[1]*img_shape[2]), dtype=np.float32)

            print(f'{split} size', len(img_list))
            for ix, img in enumerate(img_list):
                x = read_func(img)
                X[split][ix,:] = x.flatten()
            print('final shape', X[split].shape)
            np.save(os.path.join(os.environ['DATA_PATH'], f'X_flattened_{split}_{nbands}bands.npy'), X[split])
            print('{} min. saved flattenned array;'.format(int((time()-start)/60)), split)

    return X, y


def build_catalog_dataset(csv_file):
    df_orig = pd.read_csv(csv_file)

    X = {}
    y = {}

    for split in ['train', 'val', 'test']:
        print('processing', split)
        df = df_orig[df_orig.split==split]

        X[split] = df[['u','f378','f395','f410','f430','g','f515','r','f660','i','f861','z', 'fwhm']].values
        y[split] = df['class'].apply(lambda c: class_map[c]).values

    return X, y


########
# MAIN #
########


if __name__ == '__main__':

    if len(sys.argv) != 4:
        print('usage: python %s <data_dir> <csv_file> <nbands>' % sys.argv[0])
        exit(1)

    data_dir = sys.argv[1]
    csv_file = sys.argv[2]
    n_bands = int(sys.argv[3])

    print('building dataset')

    # build datasets
    X, y = build_flattened_dataset(csv_file, data_dir, n_bands)
    X_cat, y_cat = build_catalog_dataset(csv_file)

    # train log reg
    # lr_cat = LogisticRegression(
    #     max_iter=10000,
    #     multi_class='multinomial',
    #     n_jobs=-1,
    #     solver='lbfgs'
    #     ).fit(X_cat['train'], y_cat['train'])
    # print('LogisticRegression; catalog')
    # print(lr_cat.score(X_cat['val'], y_cat['val']))

    lr = LogisticRegression(
        max_iter=10000,
        multi_class='multinomial',
        n_jobs=-1,
        solver='lbfgs'
        ).fit(X['train'], y['train'])
    print('LogisticRegression; images')
    lr.score(X['val'], y['val'])