import os,sys,inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))
from callbacks import SGDRScheduler
from datagen import DataGenerator
from glob import glob
from keras import backend as K
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from keras.optimizers import SGD
import numpy as np
import pandas as pd
from models import resnext
import sklearn.metrics as metrics
from time import time
import utils


'''
NOTES

batch of 128 float32 images:
128 * 32 * (32*32*12)/8.4e6 ~= 6 MiB

class proportions:

full set
    0 GALAXY    0.5
    1 STAR      0.4
    2 QSO       0.1

subset with r in (14,18)
    0 GALAXY    0.5
    1 STAR      0.45
    2 QSO       0.05
'''


#########################
# BEGIN PARAMETER SETUP #
#########################

mode = 'train' # train, eval-mags, predict
task = 'classification' # classification or regression (magnitudes)
csv_dataset = 'csv/dr1_classes_split.csv'

n_epoch = 1000
img_dim = (32,32,12)
batch_size = 32
cardinality = 4 #16
width = 16 #4
depth = 56 #11 29

model_name = '{}_{}bands_{}'.format(task, img_dim[2], int(time()))
weights_file = None

def df_filter(df):
    # f = pd.read_csv('csv/dr1_dates_mean.csv')
    # f = f[f.year==2018]
    # f = f['field'].values # array of fields completely observed in 2018
    # df['field'] = df.id.apply(lambda s: s.split('.')[0])
    return df[(df.photoflag==0)&(df.ndet==12)] #&(df.r.between(15,19))&(df['class']=='STAR')&(df.field.isin(f))]

filter_set = True
print('photoflag=0, ndet=12, albumentations (flip)')

#######################
# END PARAMETER SETUP #
#######################

n_classes = 3 if task=='classification' else 12
class_weights = {0: 1, 1: 1.3, 2: 5} if task=='classification' else None # normalized 1/class_proportion
data_mode = 'classes' if task=='classification' else 'magnitudes'
extension = 'npy' if img_dim[2]>3 else 'png'
images_folder = '/crops_calib/' if img_dim[2]>3 else '/crops32/'
lst_activation = 'softmax' if task=='classification' else 'sigmoid'
loss = 'categorical_crossentropy' if task=='classification' else 'mean_absolute_error'
metrics_train = ['accuracy'] if task=='classification' else None
data_dir = os.getenv('HOME') + '/label_the_sky' #os.environ['DATA_PATH']
save_file = data_dir+f'/trained_models/{model_name}.h5'

print('csv_dataset', csv_dataset)
print('task', task)
print('images folder', images_folder)
print('batch_size', batch_size)
print('cardinality', cardinality)
print('depth', depth)
print('width', width)
print('nr epochs', n_epoch)
print('save_file', save_file)

params = {'data_folder': data_dir+images_folder, 'dim': img_dim, 'extension': extension, 'mode': data_mode,'n_classes': n_classes}

# load dataset iterators
df = pd.read_csv(csv_dataset)
if filter_set:
    df = df_filter(df)
imgfiles = glob(data_dir+images_folder+'*/*.'+extension)
imgfiles = [i.split('/')[-1][:-4] for i in imgfiles]
print('original df', df.shape)
df = df[df.id.isin(imgfiles)]
print('df after matching to crops', df.shape)
df_train = df[df.split=='train']
df_val = df[df.split=='val']
del df

X_train, _, labels_train = utils.get_sets(df_train, mode=data_mode)
X_val, y_true, labels_val = utils.get_sets(df_val, mode=data_mode)
print('train size', len(X_train))
print('val size', len(X_val))

train_generator = DataGenerator(X_train, labels=labels_train, batch_size=batch_size, **params)
val_generator = DataGenerator(X_val, labels=labels_val, batch_size=batch_size, **params)

# create resnext model
model = resnext(
    img_dim, depth=depth, cardinality=cardinality, width=width, classes=n_classes,
    last_activation=lst_activation, weight_decay=0)
print('model created')

# print nr params
trainable_count = int(np.sum([K.count_params(p) for p in set(model.trainable_weights)]))
non_trainable_count = int(np.sum([K.count_params(p) for p in set(model.non_trainable_weights)]))
print('Total params: {:,}'.format(trainable_count + non_trainable_count))
print('Trainable params: {:,}'.format(trainable_count))
print('Non-trainable params: {:,}'.format(non_trainable_count))

if weights_file is not None and os.path.exists(weights_file):
   model.load_weights(weights_file)
   print('model weights loaded!')

# compile model
opt = 'adam'
model.compile(loss=loss, optimizer=opt, metrics=metrics_train)

# train
if mode=='train':
    callbacks = [
        ReduceLROnPlateau(monitor='loss', factor=0.1, patience=5, verbose=1),
        #SGDRScheduler(min_lr=1e-5, max_lr=1e-2, steps_per_epoch=np.ceil(len(X_train)/batch_size), lr_decay=0.9, cycle_length=5, mult_factor=1.5),
        ModelCheckpoint(save_file, monitor='val_loss', save_best_only=True, save_weights_only=True, mode='min'),
        EarlyStopping(monitor='loss', mode='min', patience=8, restore_best_weights=True, verbose=1)
    ]

    history = model.fit_generator(
        steps_per_epoch=np.ceil(len(X_train)/batch_size),
        generator=train_generator,
        validation_data=val_generator,
        validation_steps=len(X_val)//batch_size,
        epochs=n_epoch,
        callbacks=callbacks,
        class_weight=class_weights,
        verbose=2)

    print('loss', history.history['loss'])
    print('val_loss', history.history['val_loss'])

elif mode=='eval-mags':
    mag_min = 9
    mag_max = 23
    bins = 4 # number of bins between two consecutive integers, e.g. bins=4 means [1.0, 1.25, 1.5, 1.75,]
    intervals = np.linspace(mag_min, mag_max, bins*(mag_max-mag_min)+1)
    mags = []
    acc0 = []
    acc1 = []
    acc2 = []
    for ix in range(len(intervals)-1):
        filters = {'r': (intervals[ix], intervals[ix+1])}
        X_val, y_true, _ = utils.get_sets(home_path+'/raw-data/dr1_full_val.csv', filters=filters)
        if X_val.shape[0] == 0:
            continue
        print('predicting for [{}, {}]'.format(intervals[ix], intervals[ix+1]))
        pred_generator = DataGenerator(X_val, shuffle=False, batch_size=1, **params)
        y_pred = model.predict_generator(pred_generator)
        # print(y_pred[:10])
        y_pred = np.argmax(y_pred, axis=1)

        # compute accuracy
        accuracy = metrics.accuracy_score(y_true, y_pred) * 100
        print('accuracy : ', accuracy)

        # compute confusion matrix
        cm = metrics.confusion_matrix(y_true, y_pred)
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print('confusion matrix')
        print(cm)

        if cm.shape[0]==3:
            mags.append(intervals[ix])
            acc0.append(cm[0,0])
            acc1.append(cm[1,1])
            acc2.append(cm[2,2])

    print('magnitudes', mags)
    print('accuracies for class 0', acc0)
    print('accuracies for class 1', acc1)
    print('accuracies for class 2', acc2)


# make inferences on model
print('predicting')
pred_generator = DataGenerator(X_val, shuffle=False, batch_size=1, **params)
y_pred = model.predict_generator(pred_generator, steps=len(y_true))

print(y_true[:5])
print(y_pred[:5])

if task=='classification':
    y_pred = np.argmax(y_pred, axis=1)
    preds_correct = y_pred==y_true
    print('missclasified', X_val[~preds_correct].shape)

    # compute accuracy
    accuracy = metrics.accuracy_score(y_true, y_pred) * 100
    print('accuracy : ', accuracy)

    # compute confusion matrix
    cm = metrics.confusion_matrix(y_true, y_pred)
    cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    print('confusion matrix')
    print(cm)

else:
    y_true = 30*y_true
    y_pred = 30*y_pred
    print('y_true\n', y_true[:5])
    print('y_pred\n', y_pred[:5])
    abs_errors = np.absolute(y_true - y_pred)
    np.save(f'npy/ytrue_{model_name}.npy', y_true)
    np.save(f'npy/y_{model_name}.npy', y_pred)
    np.save(f'npy/yerr_{model_name}.npy', abs_errors)

    print('absolute errors\n', abs_errors[:5])
    print('\n\nMAE:', np.mean(abs_errors))
    print('MAPE:', np.mean(abs_errors / y_true) * 100)