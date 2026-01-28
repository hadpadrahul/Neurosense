# feature_extraction.py

import numpy as np
import librosa

def extract_features(file_path):
    y, sr = librosa.load(file_path, duration=4, offset=0.5)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=22)
    return np.mean(mfcc.T, axis=0)
