import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping

# Set paths for data
processed_data_path = os.path.join('data', 'processed')
train_data_file = os.path.join(processed_data_path, 'train_data.csv')
val_data_file = os.path.join(processed_data_path, 'val_data.csv')

# Load processed training and validation data
train_data = pd.read_csv(train_data_file)
val_data = pd.read_csv(val_data_file)

# Prepare features and labels
X_train = np.array(train_data['features'].tolist())
y_train = np.array(train_data['labels'].tolist())
X_val = np.array(val_data['features'].tolist())
y_val = np.array(val_data['labels'].tolist())

# Define the model architecture
model = Sequential()
model.add(LSTM(128, input_shape=(X_train.shape[1], X_train.shape[2]), return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(64))
model.add(Dropout(0.2))
model.add(Dense(y_train.shape[1], activation='softmax'))

# Compile the model
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# Set up callbacks
checkpoint = ModelCheckpoint('model.h5', save_best_only=True, monitor='val_loss', mode='min')
early_stopping = EarlyStopping(monitor='val_loss', patience=5, mode='min')

# Train the model
model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=50, batch_size=32, callbacks=[checkpoint, early_stopping])