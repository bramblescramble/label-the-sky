'''
auxiliary funcs to generate latex-friendly plots
based on: https://jwalton.info/Embed-Publication-Matplotlib-Latex/

'''

from glob import glob
import json
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def set_size(width='thesis', fraction=1, subplots=[1, 1]):
	if width == 'thesis':
		width_pt = 468.33257
	else:
		width_pt = width

	fig_width_pt = width_pt * fraction
	inches_per_pt = 1 / 72.27 # pt to in conversion
	golden_ratio = (5**.5 - 1) / 2

	fig_width_in = fig_width_pt * inches_per_pt
	fig_height_in = fig_width_in * golden_ratio * subplots[0] / subplots[1]

	fig_dim = (fig_width_in, fig_height_in)

	return fig_dim


def make_histograms(arr, rows=3, cols=4, xmax=0.5):
	cmap = mpl.cm.get_cmap('rainbow_r', 12)
	legend = ['U', 'F378', 'F395', 'F410', 'F430', 'G', 'F515', 'R', 'F660', 'I', 'F861', 'Z']
	fig, ax = plt.subplots(rows, cols, figsize=set_size('thesis', subplots=[rows, cols]))
	plt.setp(ax, xticks=[0.1, 0.2, 0.3, 0.4, 0.5], yticks=[10000, 20000, 30000, 40000, 50000, 60000, 70000], xticklabels=[], yticklabels=[])
	n = 0
	for i in range(rows):
		for j in range(cols):
			a = arr[(arr[:,n]<=xmax),n]
			ax[i,j].hist(a, bins=25, color=cmap(12-n), edgecolor=cmap(12-n), linewidth=0.0)
			ax[i,j].set_xlabel(legend[n], labelpad=-5)
			ax[i,j].set_xlim(0, xmax)
			n = n+1
	plt.savefig('magnitude_errors.svg', format='svg', bbox_inches='tight')


def make_histograms_overlapped(arr, xmax=0.5):
	cmap = mpl.cm.get_cmap('rainbow_r', 12)
	legend = ['U', 'F378', 'F395', 'F410', 'F430', 'G', 'F515', 'R', 'F660', 'I', 'F861', 'Z']
	legend.reverse()
	print(legend)
	fig, ax = plt.subplots(figsize=set_size('thesis'))
	plt.setp(ax, xticks=[0, 0.25, 0.5], yticks=[]) #xticklabels=[])
	for n in range(11, -1, -1):
		a = arr[(arr[:,n]<=xmax),n]
		plt.hist(a, bins=50, color=cmap(n), alpha=0.5, label=legend[n])
		ax[i,j].set_xlabel(legend[n])
		ax[i,j].set_xlim(0, xmax)
		# ax[i,j].set_ylim(0, 50000)
	plt.legend()
	plt.xticks([], [])
	plt.savefig('magnitude_errors_overlap.svg', format='svg', bbox_inches='tight')


def make_history_curves(timestamp, target='magnitudes', rows=1, cols=2):
	files = glob(f'history/history_{timestamp}_*_{target}_*.json')
	print('nr of files', len(files))
	print(files)

	# ax[0] -> backbone loss
	# ax[1] -> top classifier accuracy

	plt.subplots(rows, cols, figsize=set_size('thesis', subplots=[rows, cols]))
	for f in files:
		history = json.load(open(f, 'r'))
		split = f.split('_')
		label = split[-3] + ' ' + split[-1][:-5]
		if 'clf' in f:
			acc = history['val_accuracy']
			plt.subplot(121)
			plt.plot(range(len(acc)), acc, alpha=0.9, label=label)
			# ax[1].plot(range(len(acc)), acc, alpha=0.9, label=label)
		else:
			loss = history['val_loss']
			plt.subplot(120)
			plt.plot(range(len(loss)), loss, alpha=0.9, label=label)
			# ax[0].plot(range(len(loss)), loss, alpha=0.9, label=label)
	plt.legend()
	plt.savefig(f'history_{timestamp}_{target}.svg', format='svg', bbox_inches='tight')


if __name__ == '__main__':
	plt.style.use('seaborn')

	nice_fonts = {
			# 'text.usetex': True,
			'font.family': 'serif',
			'axes.labelsize': 6,
			'font.size': 4,
			'legend.fontsize': 4,
			'xtick.labelsize': 6,
			'ytick.labelsize': 6,
	}

	mpl.rcParams.update(nice_fonts)

	# make magnitude uncertainty histograms
	# df = pd.read_csv('csv/dr1_classes_split.csv')
	# df = df.loc[:, [
	# 		'u_err','f378_err','f395_err','f410_err','f430_err','g_err',
	# 		'f515_err','r_err','f660_err','i_err','f861_err','z_err']]
	# arr = df.values
	# make_histograms(arr)

	# make training history curves
	make_history_curves(200220)
