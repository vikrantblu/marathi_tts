import argparse
import logging
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, mean_squared_error
from pathlib import Path
import torch
from torch.utils.data import DataLoader
from models import YourVoiceModel  # Replace with your actual model import
from dataset import YourDataset  # Replace with your actual dataset import

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate_model(model, dataloader):
    model.eval()
    all_predictions = []
    all_labels = []

    with torch.no_grad():
        for inputs, labels in dataloader:
            outputs = model(inputs)
            predictions = torch.argmax(outputs, dim=1)
            all_predictions.extend(predictions.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    accuracy = accuracy_score(all_labels, all_predictions)
    mse = mean_squared_error(all_labels, all_predictions)
    logger.info(f"Accuracy: {accuracy:.4f}, Mean Squared Error: {mse:.4f}")

def main(model_path, data_path, batch_size):
    # Load the trained model
    model = YourVoiceModel()  # Initialize your model
    model.load_state_dict(torch.load(model_path))
    
    # Load the validation dataset
    dataset = YourDataset(data_path)  # Initialize your dataset
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    # Evaluate the model
    evaluate_model(model, dataloader)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the trained voice model.")
    parser.add_argument("--model_path", type=str, required=True, help="Path to the trained model file.")
    parser.add_argument("--data_path", type=str, required=True, help="Path to the validation dataset.")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size for evaluation.")
    
    args = parser.parse_args()
    main(args.model_path, args.data_path, args.batch_size)