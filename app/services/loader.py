import os

def load_documents(folder_path):
    docs = []
    for file in os.listdir(folder_path):
