# -*- coding: utf-8 -*-
"""Hybrid_NN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1C_132bLs6SKw42ZyYtEC3gCRGbfEsLCg

# IMPORTS SECTION
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torchvision.transforms as transforms
import numpy as np
import os
import glob
import numpy as np
import tqdm
import matplotlib.pyplot as plt
from PIL import Image
import pandas as pd

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torch.optim as optim
import torch.utils

import torchvision
import torchvision.models as models
import torchvision.datasets as datasets
import torchvision.transforms as transforms
import albumentations as A

device = torch.device('cuda' if torch.cuda.is_available() else "cpu")

!pip install torchSummary
!pip install albumentations

"""# DATA LOADER SECTIONS

#### Mount DRIVE and FOLDERS
"""

from google.colab import drive
drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/drive/MyDrive/Garbage classification

path = "/content/drive/MyDrive/Garbage classification"
os.listdir(path)
glob.glob(path+"/*")

folders = glob.glob(path+"/*")
count = 0

for i in folders:
    count=0
    count+=len(os.listdir(i))
    print(i,' =  ', count)

"""#### Image Transformation Used"""

transform2  = A.Compose([
    A.HorizontalFlip(p=0.2),
    A.RandomBrightnessContrast(brightness_limit=0.2),
    A.VerticalFlip(p=0.2),
    A.Rotate(0,80),
    A.Resize(224,224),
    A.Normalize(max_pixel_value = 255.0,p=1)
])

"""#### Custom Dataset Object"""

import cv2
import imageio as iio
import PIL as image

class CustomDataset(Dataset):
    def __init__(self, transform = None):
        self.folder = path
        folders = glob.glob(self.folder + "/*")
#         print('folders',folders)

        self.transform = transform
        self.data = []
        for class_path in folders:
            class_name = class_path.split("/")[-1]
            for img_path in glob.glob(class_path + "/*.jpg"):
                self.data.append([img_path, class_name])

#         print(self.data[0])


        self.class_map = {
            'metal' : 0,
            'glass' : 1,
            'plastic' : 2,
            'paper':3,
            'cardboard':4,
            'trash' :5

        }
    def __len__(self):
        return len(self.data)
    def __getitem__(self, idx):
        img_path, class_name = self.data[idx]

        img = cv2.imread(img_path, cv2.IMREAD_COLOR)
        img = cv2.resize(img, (224,224))

        # Augmentations
        if self.transform is not None:
            transformed = transform2(image = img)
            transformed_image = transformed['image']
            img = cv2.resize(img,(224,224))


        class_id = self.class_map[class_name]
        img_tensor = torch.from_numpy(img)
        img_tensor = img_tensor.permute(2, 0, 1)
        img_tensor = img_tensor.to(torch.float32)

        class_id = class_id
        return img_tensor, class_id

dataset = CustomDataset(transform = transform2)
len(dataset) # 2527 images

"""#### Split Dataset to Test, Train, Validation with Dataloaders"""

dataset_size = len(dataset)
train_size = int(0.7 * dataset_size)  # 70% for training
val_size = int(0.15 * dataset_size)  # 15% for validation
test_size = dataset_size - train_size - val_size  # Remaining for test

# Use random_split to split the dataset
train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, val_size, test_size])

train_dataloader = DataLoader(train_dataset, batch_size=64, shuffle=True)
val_dataloader = DataLoader(val_dataset, batch_size=64)
test_dataloader = DataLoader(test_dataset, batch_size=64)

"""# NETWORK DEFINITION

### Primary CNN Classifier
"""

f = open("a1.txt", "w")

resnet = torchvision.models.resnet18(pretrained=True)
num_ftrs = resnet.fc.in_features

resnet.fc = nn.Linear(num_ftrs, 3)

class MPP_CGT_Classifier(nn.Module):
    def __init__(self):
        super(MPP_CGT_Classifier, self).__init__()
        # Define layers for MPP vs CGT classification
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, stride=1, padding=1)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = nn.Linear(32 * 56 * 56, 128)
        self.fc2 = nn.Linear(128, 2)  # Two classes: MPP and CGT
        self.resnet = models.resnet18(pretrained=True)
        num_ftrs = self.resnet.fc.in_features
        # Modify the output layer to match the number of classes in your subcategories (MPP or CGT)
        self.resnet.fc = nn.Linear(num_ftrs, 3)  # Change 'num_classes' accordingly

    def forward(self, x):
        # Forward pass logic
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(-1, 32 * 56 * 56)  # Flatten the tensor
        x = F.relu(self.fc1(x))
        mpp_cgt_output = self.fc2(x)
        probs = F.softmax(mpp_cgt_output, dim=1)
        # Predict the class index based on probabilities
        # _, predicted_mpp_cgt = torch.max(input = probs, dim = 1)
        _, predicted_mpp_cgt = torch.max(mpp_cgt_output, 1)
        # print(_, file = f)

        if _[0] > _[1]:
          predicted_mpp_cgt = 0
        else:
          predicted_mpp_cgt = 1

        if predicted_mpp_cgt == 0:  # MPP category
          # Pass through MPP ResNet-18
          print("BEFORE, RESNET", file = f)
          # x = x.unsqueeze(0)  # Assuming you have a single image, adds a batch dimension
          # Resize the tensor using interpolation
          x = F.interpolate(x, size=(224, 224), mode='bilinear', align_corners=False)  # Adjust size as needed
          resnet_output = self.resnet(x)
          print("AFTER, RESNET", file = f)
          return resnet_output  # Return the output from ResNet-18 for MPP category

        elif predicted_mpp_cgt == 1:  # CGT category
          # Pass through CGT ResNet-18
          print("BEFORE, RESNET", file = f)
          # x = x.unsqueeze(0)  # Assuming you have a single image, adds a batch dimension
          # Resize the tensor using interpolation
          x = F.interpolate(x, size=(224, 224), mode='bilinear', align_corners=False)  # Adjust size as needed
          resnet_output = self.resnet(x)
          print("AFTER, RESNET", file = f)
          return resnet_output  # Return the output from ResNet-18 for CGT category

mpp_cgt_classifier = MPP_CGT_Classifier()

from torchsummary import summary

mpp_cgt_classifier.to(device)
summary(mpp_cgt_classifier, (3, 224, 224))

f = open("a1.txt", "r")
print(f.read())

"""### Criterion and Optimizers for the Respective Models"""

criterion = nn.CrossEntropyLoss()
MPP_CGT_OPTIMIZER = optim.Adam(mpp_cgt_classifier.parameters(), lr = 0.001)
RESNET_MPP_OPTIMIZER = optim.Adam(resnet.parameters(), lr = 0.001)
RESNET_CGT_OPTIMIZER = optim.Adam(resnet.parameters(), lr = 0.001)
optimizer = optim.Adam(mpp_cgt_classifier.parameters(), lr = 0.001) # torch.optim.Adam(list(resnet.parameters()) + list(mpp_cgt_classifier.parameters()), lr=0.001)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.2, patience=5, verbose=True)

"""# Training

#### Evaluating Model for Validation
"""

def evaluate_model(model, dataloader, device):
    model.eval()  # for batch normalization layers
    corrects = 0
    y_pred = []
    y_true = []

    with torch.no_grad():
        for inputs, targets in dataloader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            corrects += (preds == targets.data).sum()



            output = (torch.max(torch.exp(outputs), 1)[1]).data.cpu().numpy()
            y_pred.extend(output) # Save Prediction

            labels = targets.data.cpu().numpy()
            y_true.extend(labels) # Save Truth


    print('Validation Accuracy: {:.2f}'.format(100. * corrects / len(dataloader.dataset)))
    return y_pred, y_true

"""#### Training Details"""

num_epochs = 50
val_losses = []
train_losses = []

import time
t0 = time.time()
resnet_num_epochs = 50
resnet_val_losses = []
resnet_train_losses = []

for epoch in range(resnet_num_epochs):
    train_loss= 0.0
    for i, (inputs,targets) in enumerate(train_dataloader):
        inputs = inputs.to(device)
        targets = targets.to(device)
        outputs = mpp_cgt_classifier(inputs)
        optimizer.zero_grad()
        train_loss = criterion(outputs, targets)
            #         print(train_loss.item())
            # backward pass
        train_loss.backward()
            # update parameters
        optimizer.step()
    resnet_train_losses.append(train_loss.item())

    mpp_cgt_classifier.eval()
    val_loss = 0.0
    for i, (inputs, targets) in enumerate(val_dataloader):
        inputs = inputs.to(device)
        targets = targets.to(device)

            # forward pass
        outputs = mpp_cgt_classifier(inputs)

        val_loss = criterion(outputs, targets)

    resnet_val_losses.append(val_loss.item())


    scheduler.step(val_loss)

    print('training Loss at epoch ', epoch+1 , "=" ,train_loss.item())
    print('validation Loss at epoch ', epoch+1 , "=" ,val_loss.item())
    evaluate_model(mpp_cgt_classifier, val_dataloader, device)
t1 = time.time()
print("Total time taken " ,(t1-t0)/60 )