import torch
from torch.nn.functional import conv2d
from torch import tanh
import time
import numpy as np
from .utils import accuracy, save_model

from sklearn.metrics import confusion_matrix

import pandas as pd

import copy

def train(model, optimizer, criterion, train_dl, test_dl, N_epochs, batch_size, history=None, history_model_state=[], fold=None, name=None, savedir=None, cfg=None):

    if history is None:
        history = pd.DataFrame(columns=['time', 'epoch', 'fold', 'loss_train', 'loss_test', 'acc_train', 'acc_test', 'cm_train', 'cm_test'])

    t_start = time.time()
    for epoch in range(0, N_epochs + 1):
        t_epoch = time.time()

        loss_iter = []
        for num, (xb, yb) in enumerate(train_dl):
            def closure():
                optimizer.zero_grad()
                loss = criterion(model(xb), yb.argmax(dim=1))
                loss.backward()
                return loss

            if epoch == 0: # Don't take a step and just characterize the starting structure
                with torch.no_grad():
                    loss = criterion(model(xb), yb.argmax(dim=1))
            else: # Take an optimization step
                loss = optimizer.step(closure)
                model.clip_to_design_region()

            loss_iter.append(loss.item())

        with torch.no_grad():
            acc_train_tmp = []

            list_yb_pred = []
            list_yb = []
            for num, (xb, yb) in enumerate(train_dl):
                yb_pred = model(xb)
                list_yb_pred.append(yb_pred)
                list_yb.append(yb)
                acc_train_tmp.append( accuracy(yb_pred, yb.argmax(dim=1)) )

            y_pred = torch.cat(list_yb_pred, dim=0)
            y_truth = torch.cat(list_yb, dim=0)
            cm_train = confusion_matrix(y_truth.argmax(dim=1).numpy(), y_pred.argmax(dim=1).numpy())

            acc_test_tmp = []
            loss_test_tmp = []
            list_yb_pred = []
            list_yb = []
            for num, (xb, yb) in enumerate(test_dl):
                yb_pred = model(xb)
                list_yb_pred.append(yb_pred)
                list_yb.append(yb)
                loss_test_tmp.append( criterion(yb_pred, yb.argmax(dim=1)) )
                acc_test_tmp.append( accuracy(yb_pred, yb.argmax(dim=1)) )

            y_pred = torch.cat(list_yb_pred, dim=0)
            y_truth = torch.cat(list_yb, dim=0)
            cm_test = confusion_matrix(y_truth.argmax(dim=1).numpy(), y_pred.argmax(dim=1).numpy())

        print('Epoch %2d/%2d --- Elapsed Time:  %4.2f min | Training Loss:  %.4e | Testing Loss:  %.4e | Training Accuracy:  %.4f | Testing Accuracy:  %.4f' % 
                (epoch, N_epochs, (time.time()-t_epoch)/60, np.mean(loss_iter), np.mean(loss_test_tmp), np.mean(acc_train_tmp), np.mean(acc_test_tmp)))

        history = history.append({'time': pd.to_datetime('now'),
                                  'epoch': epoch,
                                  'fold': fold,
                                  'loss_train': np.mean(loss_iter),
                                  'loss_test': np.mean(loss_test_tmp),
                                  'acc_train': np.mean(acc_train_tmp),
                                  'acc_test': np.mean(acc_test_tmp),
                                  'cm_train': cm_train,
                                  'cm_test': cm_test},
                                  ignore_index=True)

        history_model_state.append( copy.deepcopy(model.state_dict()) )

        if name is not None:
            save_model(model, name, savedir, history, history_model_state, cfg, verbose=False)

    print('Total Time: %.2f min\n' % ((time.time()-t_start)/60))

    return history, history_model_state
