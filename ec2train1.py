import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.models as models
import torchvision.transforms as transforms

import copy
import argparse
import os
import logging
import sys
from tqdm import tqdm
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

#rom torch_snippets import Report
#from torch_snippets import *

logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

def test(model, test_loader, criterion):
    model.eval()
    running_loss=0
    running_corrects=0
    
    for inputs, labels in test_loader:
        outputs=model(inputs)
        loss=criterion(outputs, labels)
        _, preds = torch.max(outputs, 1)
        running_loss += loss.item() * inputs.size(0)
        running_corrects += torch.sum(preds == labels.data)

    total_loss = running_loss / len(test_loader)
    total_acc = running_corrects.double() / len(test_loader)

def train(model, train_loader, validation_loader, criterion, optimizer):
    epochs=5
    best_loss=1e6
    image_dataset={'train':train_loader, 'valid':validation_loader}
    loss_counter=0
    #log = Report(epochs)

    for epoch in range(epochs):
        for phase in ['train', 'valid']:
            logger.info(f"Epoch: {epoch}, phase {phase}")
            if phase=='train':
                model.train()
            else:
                model.eval()
            running_loss = 0.0
            running_corrects = 0            
            running_samples=0
            
            total_samples_in_phase = len(image_dataset[phase].dataset)

            for pos,(inputs, labels) in enumerate(image_dataset[phase]):
                tot=len(image_dataset[phase])
                outputs = model(inputs)
                loss = criterion(outputs, labels)

                if phase=='train':
                    optimizer.zero_grad()
                    loss.backward()
                    #log.record(pos=(pos+1)/tot, train_loss=loss, end='\r') # impersistent data
                    optimizer.step()

                _, preds = torch.max(outputs, 1)
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                running_samples += len(inputs)
                
                accuracy = running_corrects / running_samples
                logger.debug("Epoch {}, Phase {}, Images [{}/{} ({:.0f}%)] Loss: {:.2f} Accuracy: {}/{} ({:.2f}%)".format(
                        epoch,
                        phase,
                        running_samples,
                        total_samples_in_phase,
                        100.0 * (float(running_samples) / float(total_samples_in_phase)),
                        loss.item(),
                        running_corrects,
                        running_samples,
                        100.0*accuracy,
                    ))
                
                #NOTE: Comment lines below to train and test on whole dataset
                if (running_samples>(0.1*total_samples_in_phase)):
                    break                  

            epoch_loss = running_loss / running_samples
            epoch_acc = running_corrects / running_samples
            
            if phase=='valid':
                if epoch_loss<best_loss:
                    best_loss=epoch_loss
                else:
                    loss_counter+=1
                with torch.no_grad():
                    for pos,(inputs, labels) in enumerate(image_dataset[phase]):
                        tot=len(image_dataset[phase])
                        outputs = model(inputs)
                        valid_loss = criterion(outputs, labels)
                        #log.record(pos=(pos+1)/tot, valid_loss=valid_loss, end='\r') # impersistent data
                        
            logger.info('{} loss: {:.4f}, acc: {:.4f}, best loss: {:.4f}'.format(phase,
                                                                                 epoch_loss,
                                                                                 epoch_acc,
                                                                                 best_loss))   

        if loss_counter==1:
            logger.info(f"Break due to increasing loss at epoch: {epoch}")
            break
        if epoch==0:
            logger.info(f"Break due to epoch limit at epoch: {epoch}")
            break
    return model
    
def net():
    model = models.resnet50(pretrained=True)

    for param in model.parameters():
        param.requires_grad = False   

    model.fc = nn.Sequential(
                   nn.Linear(2048, 128),
                   nn.ReLU(inplace=True),
                   nn.Linear(128, 133))
    return model

def create_data_loaders(data, batch_size):
    train_data_path = os.path.join(data, 'train')
    test_data_path = os.path.join(data, 'test')
    validation_data_path=os.path.join(data, 'valid')

    train_transform = transforms.Compose([
        transforms.RandomResizedCrop((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        ])

    test_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        ])

    train_data = torchvision.datasets.ImageFolder(root=train_data_path, transform=train_transform)
    train_data_loader = torch.utils.data.DataLoader(train_data, batch_size=batch_size, shuffle=True)

    test_data = torchvision.datasets.ImageFolder(root=test_data_path, transform=test_transform)
    test_data_loader = torch.utils.data.DataLoader(test_data, batch_size=batch_size, shuffle=True)

    validation_data = torchvision.datasets.ImageFolder(root=validation_data_path, transform=test_transform)
    validation_data_loader = torch.utils.data.DataLoader(validation_data, batch_size=batch_size, shuffle=True) 
    
    return train_data_loader, test_data_loader, validation_data_loader

if __name__=='__main__':
    logger.info("Starting program")
    logger.debug("Creatinng data loaders")
    batch_size=32
    learning_rate=1e-4
    train_loader, test_loader, validation_loader=create_data_loaders('dogImages',batch_size)
    model=net()

    criterion = nn.CrossEntropyLoss(ignore_index=133)
    optimizer = optim.Adam(model.fc.parameters(), lr=learning_rate)

    logger.info("Starting Model Training")
    model=train(model, train_loader, validation_loader, criterion, optimizer)
    torch.save(model.state_dict(), 'TrainedModels/model.pth')
    logger.info('Model saved.')

