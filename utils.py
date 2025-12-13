import os
import pandas as pd
import config

def create_img_folders(folder_path=config.IMAGES_BASE_PATH, categories_path=config.CSV_FILE_PATH):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    categories = pd.read_csv(categories_path)

    for category in categories['category'].unique():
        if not os.path.exists(os.path.join(folder_path, category)):
            os.makedirs(os.path.join(folder_path, category))

if __name__ == "__main__":
    create_img_folders()