'''
auxiliary funcs to generate latex-friendly plots
based on: https://jwalton.info/Embed-Publication-Matplotlib-Latex/

'''

from constants import CLASS_MAP
from glob import glob
import json
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import auc
from umap import UMAP


COLORS = ['#1240AB', '#FFAA00', '#CD0074', '#00CC00']
COLORS_PAIRED = ['#1240AB', '#6C8CD5', '#FFAA00', '#FFD073', '#CD0074', '#E667AF', '#00CC00', '#67E667']
LEGEND_LOCATION = 'lower right'


def set_plt_style():
    plt.style.use('seaborn')
    nice_fonts = {
            'text.usetex': False,#True,
            'font.family': 'serif',
            'axes.labelsize': 6,
            'font.size': 8,
            'legend.fontsize': 6,
            'xtick.labelsize': 6,
            'ytick.labelsize': 6,
    }
    mpl.rcParams.update(nice_fonts)

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

def clear_plot():
    plt.clf()

def set_colors(ax, paired=False, pos_init=0):
    # blue, yellow, pink, green
    # 12, 5, 3, imagenet
    if paired:
        pallete = COLORS_PAIRED
    else:
        pallete = COLORS
    pos = pos_init*2 if paired else pos_init
    pallete = pallete[pos:]
    ax.set_prop_cycle(color=pallete)

def metric_curve(file_list, plt_labels, output_file, paired=False, color_pos=0, metric='val_loss', legend_location=LEGEND_LOCATION):
    _, ax = plt.subplots(figsize=set_size(), clear=True)
    set_colors(ax=ax, paired=paired, pos_init=color_pos)

    max_iterations = -1
    for ix, filename in enumerate(file_list):
        history = json.load(open(filename, 'r'))
        metric_ = [run[f'{metric}'] for run in history]
        metric_ = np.array(metric_)
        means = metric_.mean(axis=0)
        errors = metric_.std(axis=0, ddof=1)
        iterations = range(means.shape[0])
        if means.shape[0] > max_iterations:
            max_iterations = means.shape[0]
        plt.plot(iterations, means, linewidth=1, label=plt_labels[ix])
        plt.fill_between(iterations, means-errors, means+errors, alpha=0.5)
    plt.legend(loc=legend_location)
    plt.xlim(0, max_iterations)
    plt.xlabel('# of iterations')
    plt.ylabel(metric)
    plt.savefig(output_file, format='pdf', bbox_inches='tight')

def score_attribute_scatter(
    yhat_files, plt_labels, output_file, dataset_file, split, attribute,
    legend_location=LEGEND_LOCATION):
    '''
        yhat_files:     list of npy filepaths with y_hat outputs, shape (n_samples, n_classes)
        dataset_file:   path of csv file 
        split:          dataset split from which yhat was computed (train, val, test)
        attribute:      object attribute to plot on x-axis (fwhm, magnitude, magnitude error)
        output_file:    path of output image
    '''
    _, ax = plt.subplots(figsize=set_size(), clear=True)
    set_colors(ax=ax)

    df = pd.read_csv(dataset_file)
    if attribute not in df.columns:
        raise ValueError('attribute must be one of:', df.columns)

    df = df[df.split==split]
    attribute_vals = df[attribute].values
    class_names = df['class'].values
    y = [CLASS_MAP[c] for c in class_names] # ground truth class of each sample

    for ix, yhat_file in enumerate(yhat_files):
        yhat = np.load(yhat_file)
        yhat_scores = yhat[range(yhat.shape[0]), y] # get scores predicted for ground truth classes
        plt.scatter(attribute_vals, np.log(yhat_scores), label=plt_labels[ix], alpha=0.2, s=2)
    plt.xlabel(attribute)
    plt.ylabel('yhat')
    plt.legend(loc=legend_location)
    plt.savefig(output_file, format='pdf', bbox_inches='tight')

def acc_attribute_curve(
    file_list, plt_labels, output_file, dataset_file, split, attribute,
    paired=False, nbins=100, legend_location=LEGEND_LOCATION):
    '''
    plot accuracy vs attribute curve. use bins with approximately uniform number of samples.
    '''
    _, ax = plt.subplots(figsize=set_size(), clear=True)
    set_colors(ax=ax, paired=paired)

    df = pd.read_csv(dataset_file)
    if attribute not in df.columns:
        raise ValueError('attribute must be one of:', df.columns)

    df = df[df.split==split]
    attribute_vals = df[attribute].values
    class_names = df['class'].values
    y = np.array([CLASS_MAP[c] for c in class_names]) # ground truth class of each sample

    sorted_idx = np.argsort(attribute_vals)
    attribute_vals = attribute_vals[sorted_idx]
    attribute_vals = np.array_split(attribute_vals, nbins)
    attribute_vals = [np.median(subarr) for subarr in attribute_vals]

    y = y[sorted_idx]

    n = len(file_list)
    for ix, f in enumerate(file_list):
        yhat = np.load(f)
        yhat = np.argmax(yhat, axis=1)
        yhat = yhat[sorted_idx]
        is_correct = yhat==y
        is_correct = np.array_split(is_correct, nbins)
        acc = [sum(subarr) / len(subarr) for subarr in is_correct]
        area = round(auc(attribute_vals, acc), 4)
        plt.plot(attribute_vals, acc, label=plt_labels[ix] + '; AUC: ' + str(area), zorder=n-ix, linewidth=1)
    plt.xlabel(attribute)
    plt.ylabel('val_accuracy')
    plt.legend(loc=legend_location)
    plt.savefig(output_file, format='pdf', bbox_inches='tight')

def lowdata_curve(
    file_list, plt_labels, output_file,
    paired=False, color_pos=0, metric='val_accuracy', agg_fn=np.max, size_increment=100, n_subsets=20, legend_location=LEGEND_LOCATION):
    _, ax = plt.subplots(figsize=set_size(), clear=True)
    set_colors(ax=ax, paired=paired, pos_init=color_pos)

    n = len(file_list)
    for ix, f in enumerate(file_list):
        history = json.load(open(f, 'r'))
        metric_means = []
        metric_stds = []
        sample_sizes = [size_increment*n for n in range(1, n_subsets+1)]
        for run_history in history:
            metrics = np.array([agg_fn(run[f'{metric}']) for run in run_history])
            metric_means.append(metrics.mean())
            metric_stds.append(metrics.std(ddof=1))
        metric_means = np.array(metric_means)
        metric_stds = np.array(metric_stds)
        plt.plot(sample_sizes, metric_means, label=plt_labels[ix], alpha=0.8, zorder=n-ix, linewidth=1)
        plt.fill_between(sample_sizes, metric_means-metric_stds, metric_means+metric_stds, alpha=0.5)
    plt.legend(loc=legend_location)
    plt.xlabel('# of samples')
    plt.ylabel(metric)
    plt.savefig(output_file, format='pdf', bbox_inches='tight')

def umap_scatter(
    file_list, plt_labels, output_file,
    dataset_file=None, split=None, color_attribute=None, n_neighbors=200, legend_location=LEGEND_LOCATION):
    ncols, nrows = 2, np.ceil(len(file_list)/2).astype(int)
    subplots = [nrows, ncols]
    _, ax = plt.subplots(nrows=nrows, ncols=ncols, figsize=set_size(subplots=subplots), clear=True)

    if color_attribute:
        df = pd.read_csv(dataset_file)
        df = df[df.split==split]
        y = df[color_attribute].values
        colors = [COLORS[CLASS_MAP[c]] for c in y]

    for ix, f in enumerate(file_list):
        X_f = np.load(f)
        X_umap = UMAP(n_neighbors=n_neighbors, random_state=42).fit_transform(X_f)
        if color_attribute:
            ax[ix//2, ix%2].scatter(X_umap[:, 0], X_umap[:, 1], alpha=0.1, s=1.5, c=colors)
        else:
            ax[ix//2, ix%2].scatter(X_umap[:, 0], X_umap[:, 1], alpha=0.1, s=1.5, c=COLORS[ix])
        ax[ix//2, ix%2].set_xticks([])
        ax[ix//2, ix%2].set_yticks([])
        ax[ix//2, ix%2].set_xlabel(plt_labels[ix])

    if color_attribute and color_attribute=='class':
        plt.legend(loc=legend_location)
    plt.savefig(output_file, format='pdf', bbox_inches='tight')

def missclassified_samples(yhat, crops_path, dataset_file, output_file, n=10):
    raise NotImplementedError
