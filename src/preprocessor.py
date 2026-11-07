"""
IDS Project - Data Preprocessor Module
========================================
Handles data cleaning, encoding, scaling, and train/test splitting.
Follows ML best practices: split FIRST, then fit preprocessing on train only.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from typing import Tuple, Optional

PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"


class IDSPreprocessor:
    """
    End-to-end preprocessing pipeline for IDS datasets.
    Handles cleaning, encoding, scaling with proper train/test discipline.
    """
    
    def __init__(self):
        self.label_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.target_column = None
        self.label_mapping = None
        self.is_fitted = False
    
    def clean(self, df: pd.DataFrame, target_col: str = "Label") -> pd.DataFrame:
        """
        Step 1: Clean the raw dataset.
        - Remove duplicates
        - Handle missing values
        - Replace infinity values
        - Remove constant columns
        
        Args:
            df: Raw DataFrame
            target_col: Name of the target/label column
        
        Returns:
            Cleaned DataFrame
        """
        print("🧹 Step 1: Cleaning data...")
        self.target_column = target_col
        original_shape = df.shape
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        # 1. Remove duplicate rows
        n_dupes = df.duplicated().sum()
        if n_dupes > 0:
            df = df.drop_duplicates().reset_index(drop=True)
            print(f"   ✅ Removed {n_dupes:,} duplicate rows")
        
        # 2. Replace infinity values with NaN
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        inf_count = np.isinf(df[numeric_cols].values).sum()
        if inf_count > 0:
            df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
            print(f"   ✅ Replaced {inf_count:,} infinity values with NaN")
        
        # 3. Handle missing values
        missing_total = df.isnull().sum().sum()
        if missing_total > 0:
            # For numeric columns: fill with median
            for col in numeric_cols:
                if df[col].isnull().any():
                    df[col] = df[col].fillna(df[col].median())
            
            # For categorical columns: fill with mode
            cat_cols = df.select_dtypes(include=['object']).columns
            for col in cat_cols:
                if col != target_col and df[col].isnull().any():
                    df[col] = df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else 'unknown')
            
            # Drop rows where target is missing
            if df[target_col].isnull().any():
                n_missing_target = df[target_col].isnull().sum()
                df = df.dropna(subset=[target_col]).reset_index(drop=True)
                print(f"   ✅ Dropped {n_missing_target} rows with missing target")
            
            print(f"   ✅ Handled {missing_total:,} missing values (median/mode imputation)")
        
        # 4. Remove constant columns (zero variance)
        constant_cols = [col for col in numeric_cols if df[col].nunique() <= 1]
        if constant_cols:
            df = df.drop(columns=constant_cols)
            print(f"   ✅ Removed {len(constant_cols)} constant columns: {constant_cols}")
        
        print(f"   📊 Shape: {original_shape} → {df.shape}")
        return df
    
    def encode_target(self, df: pd.DataFrame, binary: bool = False) -> pd.DataFrame:
        """
        Step 2: Encode the target variable.
        
        Args:
            df: Cleaned DataFrame
            binary: If True, encode as binary (Normal=0, Attack=1).
                    If False, encode each attack type separately.
        
        Returns:
            DataFrame with encoded target
        """
        print("🏷️  Step 2: Encoding target variable...")
        
        target = df[self.target_column].copy()
        
        if binary:
            # Binary classification: Normal vs Attack
            # CIC-IDS2017 uses 'BENIGN', UNSW-NB15 uses 'Normal'
            normal_labels = ['BENIGN', 'benign', 'Normal', 'normal', '0']
            df['target'] = target.apply(
                lambda x: 0 if str(x).strip() in normal_labels else 1
            )
            self.label_mapping = {0: 'Normal', 1: 'Attack'}
            print(f"   ✅ Binary encoding: Normal=0, Attack=1")
        else:
            # Multi-class classification
            self.label_encoder.fit(target)
            df['target'] = self.label_encoder.transform(target)
            self.label_mapping = dict(
                zip(self.label_encoder.transform(self.label_encoder.classes_),
                    self.label_encoder.classes_)
            )
            print(f"   ✅ Multi-class encoding: {len(self.label_mapping)} classes")
        
        # Print class distribution
        dist = df['target'].value_counts().sort_index()
        for val, count in dist.items():
            label = self.label_mapping.get(val, val)
            pct = count / len(df) * 100
            print(f"      {val} ({label}): {count:,} ({pct:.1f}%)")
        
        return df
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Step 3: Extract and prepare feature matrix.
        - Drop non-numeric columns (except encoded ones)
        - Drop target/label columns from features
        
        Args:
            df: DataFrame with encoded target
        
        Returns:
            DataFrame with only numeric feature columns + 'target'
        """
        print("🔧 Step 3: Extracting features...")
        
        # Columns to exclude from features
        exclude_cols = {self.target_column, 'target', 'Label', 'label', 
                       'attack_cat', 'Attack', 'class', 'id', 'Timestamp',
                       'Flow ID', 'Source IP', 'Destination IP', 'Src IP', 'Dst IP'}
        
        # Get numeric columns only
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.feature_columns = [c for c in numeric_cols if c not in exclude_cols]
        
        print(f"   ✅ Selected {len(self.feature_columns)} numeric features")
        print(f"   📋 Sample features: {self.feature_columns[:5]}...")
        
        return df
    
    def split_data(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        val_size: float = 0.1,
        random_state: int = 42
    ) -> dict:
        """
        Step 4: Split data into train/validation/test sets.
        IMPORTANT: Split BEFORE scaling!
        
        Args:
            df: DataFrame with features and 'target' column
            test_size: Fraction for test set
            val_size: Fraction for validation set (from training data)
            random_state: Random seed
        
        Returns:
            dict with X_train, X_val, X_test, y_train, y_val, y_test
        """
        print("✂️  Step 4: Splitting data...")
        
        X = df[self.feature_columns].values
        y = df['target'].values
        
        # First split: train+val / test
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Second split: train / val
        if val_size > 0:
            val_fraction = val_size / (1 - test_size)
            X_train, X_val, y_train, y_val = train_test_split(
                X_temp, y_temp, test_size=val_fraction, 
                random_state=random_state, stratify=y_temp
            )
            print(f"   ✅ Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")
        else:
            X_train, X_val, y_train, y_val = X_temp, None, y_temp, None
            print(f"   ✅ Train: {len(X_train):,} | Test: {len(X_test):,}")
        
        return {
            'X_train': X_train, 'X_val': X_val, 'X_test': X_test,
            'y_train': y_train, 'y_val': y_val, 'y_test': y_test
        }
    
    def scale_features(self, data: dict) -> dict:
        """
        Step 5: Scale features using StandardScaler.
        FIT on training data only, TRANSFORM all sets.
        
        Args:
            data: dict from split_data()
        
        Returns:
            dict with scaled features
        """
        print("📏 Step 5: Scaling features (fit on train only)...")
        
        # Fit on training data ONLY
        self.scaler.fit(data['X_train'])
        self.is_fitted = True
        
        data['X_train'] = self.scaler.transform(data['X_train'])
        data['X_test'] = self.scaler.transform(data['X_test'])
        
        if data['X_val'] is not None:
            data['X_val'] = self.scaler.transform(data['X_val'])
        
        print(f"   ✅ Features scaled (mean≈0, std≈1)")
        return data
    
    def preprocess(
        self,
        df: pd.DataFrame,
        target_col: str = "Label",
        binary: bool = False,
        test_size: float = 0.2,
        val_size: float = 0.1,
        save: bool = True
    ) -> Tuple[dict, 'IDSPreprocessor']:
        """
        Run the complete preprocessing pipeline.
        
        Args:
            df: Raw DataFrame
            target_col: Target column name
            binary: Binary or multi-class classification
            test_size: Test set fraction
            val_size: Validation set fraction
            save: Whether to save processed data and preprocessor
        
        Returns:
            Tuple of (data_dict, preprocessor)
        """
        print("\n" + "="*60)
        print("🔄 Running Full Preprocessing Pipeline")
        print("="*60 + "\n")
        
        # Run pipeline
        df = self.clean(df, target_col)
        df = self.encode_target(df, binary=binary)
        df = self.extract_features(df)
        data = self.split_data(df, test_size=test_size, val_size=val_size)
        data = self.scale_features(data)
        
        if save:
            self.save(data)
        
        print("\n" + "="*60)
        print("✅ Preprocessing Complete!")
        print("="*60)
        
        return data, self
    
    def save(self, data: dict, output_dir: str = None):
        """Save processed data and preprocessor to disk."""
        if output_dir is None:
            output_dir = str(DATA_PROCESSED)
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Save numpy arrays
        for key, arr in data.items():
            if arr is not None:
                np.save(os.path.join(output_dir, f"{key}.npy"), arr)
        
        # Save preprocessor
        preprocessor_data = {
            'label_encoder': self.label_encoder,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'target_column': self.target_column,
            'label_mapping': self.label_mapping,
        }
        joblib.dump(preprocessor_data, os.path.join(output_dir, "preprocessor.pkl"))
        
        print(f"\n💾 Saved processed data to: {output_dir}")
    
    @classmethod
    def load(cls, input_dir: str = None) -> Tuple[dict, 'IDSPreprocessor']:
        """Load processed data and preprocessor from disk."""
        if input_dir is None:
            input_dir = str(DATA_PROCESSED)
        
        # Load numpy arrays
        data = {}
        for key in ['X_train', 'X_val', 'X_test', 'y_train', 'y_val', 'y_test']:
            path = os.path.join(input_dir, f"{key}.npy")
            if os.path.exists(path):
                data[key] = np.load(path)
            else:
                data[key] = None
        
        # Load preprocessor
        preprocessor = cls()
        prep_data = joblib.load(os.path.join(input_dir, "preprocessor.pkl"))
        preprocessor.label_encoder = prep_data['label_encoder']
        preprocessor.scaler = prep_data['scaler']
        preprocessor.feature_columns = prep_data['feature_columns']
        preprocessor.target_column = prep_data['target_column']
        preprocessor.label_mapping = prep_data['label_mapping']
        preprocessor.is_fitted = True
        
        print(f"✅ Loaded processed data from: {input_dir}")
        print(f"   Train: {data['X_train'].shape} | Test: {data['X_test'].shape}")
        
        return data, preprocessor


import os  # needed for save/load
