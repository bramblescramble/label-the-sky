from glob import glob
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d, Axes3D
import numpy as np
from time import time


filepattern = '../raw-data/crops/*.npy'
file = '../raw-data/crops/SPLUS.STRIPE82-0058.01798.npy'


def plot_3d(img):
    x, y = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    fig = plt.figure()
    ax = Axes3D(fig)
    ax.plot_surface(x, y, img, rstride=1, cstride=1, cmap=plt.cm.gray, linewidth=0)
    plt.show()


# from http://bugra.github.io/work/notes/2014-03-31/outlier-detection-in-time-series-signals-fft-median-filtering/
# TODO: what would be a good threshold?
def get_median_filtered(signal, threshold=5):
    signal = signal.copy()
    difference = np.abs(signal - np.median(signal))
    median_difference = np.median(difference)
    if median_difference == 0:
        s = 0
    else:
        s = difference / float(median_difference)
    mask = s > threshold
    signal[mask] = np.median(signal)
    return signal


# TODO: min and max for each band
def get_min_max(filefolder):
	start = time()
	files = glob(filefolder)
	minimum, maximum = 0., 0.
	min_file, max_file = '', ''
	n_files = len(files)
	print('nr of files', n_files)
	for ix, file in enumerate(files):
		im = np.load(file)
		min_tmp, max_tmp = np.min(im), np.max(im)
		if min_tmp < minimum:
			minimum = min_tmp
			min_file = file
		if max_tmp > maximum:
			maximum = max_tmp
			max_file = file
		# display progress in 10% steps
		# r = np.round(ix/n_files,2)
		# if r>0 and r % 0.1 == 0:
		# 	print('processed {} after {} min'.format(r, int((time()-start)/60)))
	print('minutes taken:', int((time()-start)/60))

	print('min: {} in {}'.format(minimum, min_file))
	print('max: {} in {}'.format(maximum, max_file))


# get_min_max(filepattern)

print(file)
im = np.load(file) #channels-last; idx 7 is R
idx_max = np.unravel_index(np.argmax(im, axis=None), im.shape)

# get min and max along each channel
print('min:', np.min(im, axis=(0,1)))
print('max:', np.max(im, axis=(0,1)))
print('argmax:', idx_max)

# returns one band (the one that has the maximum) filtered by the median
im_filtered = get_median_filtered(im[:,:,idx_max[2]])
# plot_3d(im[:,:,idx_max[2]])
# plot_3d(im_filtered)
