#   This file is part of the markovmodel/deeptime repository.
#   Copyright (C) 2017 Computational Molecular Biology Group,
#   Freie Universitaet Berlin (GER)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
A simple API to apply PCA, TICA, and AE to time series data.
'''

from .models import PCA as _PCA
from .models import TICA as _TICA
from .models import AE as _AE
from .utils import create_dataset as _create_dataset
from .utils import random_split as _random_split
from .utils import whiten_data as _whiten_data
from torch import nn as _nn
from torch.utils.data import DataLoader as _DataLoader

def _transform(model, data, data_0, batch_size, whiten):
    loader = _DataLoader(data_0, batch_size=batch_size)
    if whiten:
        transformed_data = _whiten_data(model.transform(loader)).numpy()
    else:
        transformed_data = model.transform(loader).numpy()
    if isinstance(data, (list, tuple)):
        collect = []
        p = 0
        lengths = [d.shape[0] for d in data]
        for length in lengths:
            collect.append(transformed_data[p:p+length, :])
            p += length
        return collect
    return transformed_data

def pca(data, dim=None, validation_split=None, batch_size=100, whiten=False):
    '''Perform a principal component analysis for dimensionality reduction.

    We compute the first <dim> eigenvectors of the instantaneous covariance
    matrix and use them to rotate/project the data into a lower dimensional
    subspace.

    Arguments:
        data (numpy-ndarray of list thereof): the data to be transformed
        dim (int): the target dimensionality
        validation_split (float): fraction of the data reserved for validation
        batch_size (int): specify a batch size for the minibatch process
        whiten (boolean): set to True to whiten the transformed data

    Returns:
        (numpy.ndarray of list thereof): the transformed data
        (float): training loss
        (float): validation loss
    '''
    data_0 = _create_dataset(data, lag=0)
    if validation_split is None:
        train_loader = _DataLoader(data_0, batch_size=batch_size)
        test_loader = None
    else:
        data_test, data_train = _random_split(
            data_0, f_active=validation_split)
        train_loader = _DataLoader(data_train, batch_size=batch_size)
        test_loader = _DataLoader(data_test, batch_size=batch_size)
    model = _PCA()
    train_loss, test_loss = model.fit(
        train_loader, dim=dim, test_loader=test_loader)
    transformed_data = _transform(model, data, data_0, batch_size, whiten)
    return transformed_data, train_loss, test_loss

def tica(
    data, dim=None, lag=1, kinetic_map=True, symmetrize=False,
    validation_split=None, batch_size=100, whiten=False):
    '''Perform a time-lagged independent component analysis for
    dimensionality reduction.

    We compute a rank-d approximation to the Koopman operator and use it to
    rotate/project the data into a lower dimensional subspace.

    Arguments:
        data (numpy-ndarray of list thereof): the data to be transformed
        dim (int): the target dimensionality
        lag (int): specifies the lag in time steps
        kinetic_map (boolean): use the kinetic map variant of TICA
        symmetrize (boolean): enforce symmetry and reversibility
        validation_split (float): fraction of the data reserved for validation
        batch_size (int): specify a batch size for the minibatch process
        whiten (boolean): set to True to whiten the transformed data

    Returns:
        (numpy.ndarray of list thereof): the transformed data
        (float): training loss
        (float): validation loss
    '''
    data_0 = _create_dataset(data, lag=0)
    data_lag = _create_dataset(data, lag=lag)
    if validation_split is None:
        train_loader = _DataLoader(data_lag, batch_size=batch_size)
        test_loader = None
    else:
        data_test, data_train = _random_split(
            data_lag, f_active=validation_split)
        train_loader = _DataLoader(data_train, batch_size=batch_size)
        test_loader = _DataLoader(data_test, batch_size=batch_size)
    model = _TICA(kinetic_map=kinetic_map, symmetrize=symmetrize)
    train_loss, test_loss = model.fit(
        train_loader, dim=dim, test_loader=test_loader)
    transformed_data = _transform(model, data, data_0, batch_size, whiten)
    return transformed_data, train_loss, test_loss

def ae(
    data, dim=None, lag=1, n_epochs=50, validation_split=None,
    batch_size=100, whiten=False, **kwargs):
    '''Use a time-lagged autoencoder model for dimensionality reduction.

    We train a deep (or shallow) time-lagged autoencoder type neural network
    and use the first half (encoder stage) to transform the supplied data.

    Arguments:
        data (numpy-ndarray of list thereof): the data to be transformed
        dim (int): the target dimensionality
        lag (int): specifies the lag in time steps
        n_epochs (int): number of training epochs
        validation_split (float): fraction of the data reserved for validation
        batch_size (int): specify a batch size for the minibatch process
        whiten (boolean): set to True to whiten the transformed data

    Returns:
        (numpy.ndarray of list thereof): the transformed data
        (float): training loss
        (float): validation loss
    '''
    ae_args = dict(
        hid_size=[100],
        dropout=_nn.Dropout(p=0.5),
        activation=_nn.LeakyReLU(),
        lat_activation=None,
        batch_normalization=None,
        bias=True,
        lr=0.001,
        cuda=False)
    ae_args.update(kwargs)
    try:
        size = data.shape[1]
    except AttributeError:
        size = data[0].shape[1]
    data_0 = _create_dataset(data, lag=0)
    data_lag = _create_dataset(data, lag=lag)
    if validation_split is None:
        train_loader = _DataLoader(data_lag, batch_size=batch_size)
        test_loader = None
    else:
        data_test, data_train = _random_split(
            data_lag, f_active=validation_split)
        train_loader = _DataLoader(data_train, batch_size=batch_size)
        test_loader = _DataLoader(data_test, batch_size=batch_size)
    model = _AE(size, dim, **ae_args)
    train_loss, test_loss = model.fit(
        train_loader, n_epochs, test_loader=test_loader)
    transformed_data = _transform(model, data, data_0, batch_size, whiten)
    return transformed_data, train_loss, test_loss
