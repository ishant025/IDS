"""
IDS Project - Data Loader Module
=================================
Downloads and loads CIC-IDS2017 and UNSW-NB15 datasets.
Provides utilities for dataset validation and basic info.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path


# ============================================
# Dataset Paths
# ============================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"


def download_cicids2017(data_dir: str = None) -> str:
    """
    Download CIC-IDS2017 dataset from Kaggle.
    
    Returns:
        str: Path to the downloaded dataset directory
    """
    if data_dir is None:
        data_dir = str(DATA_RAW / "cicids2017")
    
    os.makedirs(data_dir, exist_ok=True)
    
    try:
        import kagglehub
        path = kagglehub.dataset_download(
            "cicdataset/cicids2017",
            path=data_dir
        )
        print(f"✅ CIC-IDS2017 downloaded to: {path}")
        return path
    except Exception as e:
        print(f"⚠️  Kagglehub download failed: {e}")
        print("Trying opendatasets...")
        try:
            import opendatasets as od
            od.download(
                "https://www.kaggle.com/datasets/cicdataset/cicids2017",
                data_dir=str(DATA_RAW)
            )
            print(f"✅ CIC-IDS2017 downloaded via opendatasets to: {data_dir}")
            return data_dir
        except Exception as e2:
            print(f"❌ Download failed: {e2}")
            print("\n📥 Manual download instructions:")
            print("1. Go to: https://www.kaggle.com/datasets/cicdataset/cicids2017")
            print(f"2. Download and extract CSVs to: {data_dir}")
            return data_dir


def download_unsw_nb15(data_dir: str = None) -> str:
    """
    Download UNSW-NB15 dataset from Kaggle.
    
    Returns:
        str: Path to the downloaded dataset directory
    """
    if data_dir is None:
        data_dir = str(DATA_RAW / "unsw_nb15")
    
    os.makedirs(data_dir, exist_ok=True)
    
    try:
        import kagglehub
        path = kagglehub.dataset_download(
            "mrwellsdavid/unsw-nb15",
            path=data_dir
        )
        print(f"✅ UNSW-NB15 downloaded to: {path}")
        return path
    except Exception as e:
        print(f"⚠️  Kagglehub download failed: {e}")
        try:
            import opendatasets as od
            od.download(
                "https://www.kaggle.com/datasets/mrwellsdavid/unsw-nb15",
                data_dir=str(DATA_RAW)
            )
            print(f"✅ UNSW-NB15 downloaded via opendatasets to: {data_dir}")
            return data_dir
        except Exception as e2:
            print(f"❌ Download failed: {e2}")
            print("\n📥 Manual download instructions:")
            print("1. Go to: https://www.kaggle.com/datasets/mrwellsdavid/unsw-nb15")
            print(f"2. Download and extract CSVs to: {data_dir}")
            return data_dir


def load_cicids2017(data_dir: str = None, sample_frac: float = None) -> pd.DataFrame:
    """
    Load all CIC-IDS2017 CSV files into a single DataFrame.
    
    Args:
        data_dir: Path to raw dataset directory. If None, uses default.
        sample_frac: Fraction of data to sample (0-1). None for full dataset.
    
    Returns:
        pd.DataFrame: Combined dataset
    """
    if data_dir is None:
        data_dir = str(DATA_RAW / "cicids2017")
    
    csv_files = []
    for root, dirs, files in os.walk(data_dir):
        for f in files:
            if f.endswith('.csv'):
                csv_files.append(os.path.join(root, f))
    
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {data_dir}. "
            "Please download the dataset first using download_cicids2017()"
        )
    
    print(f"📂 Found {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"   - {os.path.basename(f)}")
    
    dfs = []
    for f in csv_files:
        print(f"   Loading {os.path.basename(f)}...", end=" ")
        try:
            df = pd.read_csv(f, encoding='utf-8', low_memory=False)
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()
            dfs.append(df)
            print(f"✅ ({len(df)} rows)")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if not dfs:
        raise ValueError("No CSV files could be loaded successfully.")
    
    combined = pd.concat(dfs, ignore_index=True)
    print(f"\n✅ Total combined: {combined.shape[0]} rows × {combined.shape[1]} columns")
    
    if sample_frac is not None and 0 < sample_frac < 1:
        combined = combined.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
        print(f"📊 Sampled {sample_frac*100:.0f}%: {len(combined)} rows")
    
    return combined


def load_unsw_nb15(data_dir: str = None, sample_frac: float = None) -> pd.DataFrame:
    """
    Load UNSW-NB15 dataset into a DataFrame.
    
    Args:
        data_dir: Path to raw dataset directory
        sample_frac: Fraction of data to sample (0-1)
    
    Returns:
        pd.DataFrame: Dataset
    """
    if data_dir is None:
        data_dir = str(DATA_RAW / "unsw_nb15")
    
    csv_files = []
    for root, dirs, files in os.walk(data_dir):
        for f in files:
            if f.endswith('.csv'):
                csv_files.append(os.path.join(root, f))
    
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {data_dir}. "
            "Please download the dataset first using download_unsw_nb15()"
        )
    
    print(f"📂 Found {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"   - {os.path.basename(f)}")
    
    # Try loading the main training/testing files first
    train_files = [f for f in csv_files if 'train' in os.path.basename(f).lower()]
    test_files = [f for f in csv_files if 'test' in os.path.basename(f).lower()]
    
    if train_files and test_files:
        print("   Found train/test split files, loading separately...")
        train_df = pd.read_csv(train_files[0], low_memory=False)
        test_df = pd.read_csv(test_files[0], low_memory=False)
        combined = pd.concat([train_df, test_df], ignore_index=True)
    else:
        # Load all CSVs
        dfs = []
        for f in csv_files:
            try:
                df = pd.read_csv(f, low_memory=False)
                dfs.append(df)
                print(f"   Loaded {os.path.basename(f)}: {len(df)} rows")
            except Exception as e:
                print(f"   ❌ Error loading {os.path.basename(f)}: {e}")
        combined = pd.concat(dfs, ignore_index=True)
    
    # Strip whitespace from column names
    combined.columns = combined.columns.str.strip()
    
    print(f"\n✅ Total: {combined.shape[0]} rows × {combined.shape[1]} columns")
    
    if sample_frac is not None and 0 < sample_frac < 1:
        combined = combined.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
        print(f"📊 Sampled {sample_frac*100:.0f}%: {len(combined)} rows")
    
    return combined


def dataset_info(df: pd.DataFrame, name: str = "Dataset") -> dict:
    """
    Print comprehensive dataset information.
    
    Args:
        df: DataFrame to analyze
        name: Name of the dataset for display
    
    Returns:
        dict: Summary statistics
    """
    print(f"\n{'='*60}")
    print(f"📊 {name} — Summary")
    print(f"{'='*60}")
    
    info = {
        "rows": len(df),
        "columns": len(df.columns),
        "memory_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
        "missing_total": df.isnull().sum().sum(),
        "duplicate_rows": df.duplicated().sum(),
    }
    
    print(f"  Rows:           {info['rows']:,}")
    print(f"  Columns:        {info['columns']}")
    print(f"  Memory:         {info['memory_mb']:.1f} MB")
    print(f"  Missing Values: {info['missing_total']:,}")
    print(f"  Duplicate Rows: {info['duplicate_rows']:,}")
    
    print(f"\n  Column Types:")
    for dtype, count in df.dtypes.value_counts().items():
        print(f"    {dtype}: {count}")
    
    # Check for infinity values in numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    inf_count = np.isinf(df[numeric_cols].values).sum() if len(numeric_cols) > 0 else 0
    info["infinity_values"] = inf_count
    print(f"\n  Infinity Values: {inf_count:,}")
    
    # Missing values per column (top 10)
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if len(missing) > 0:
        print(f"\n  Top Missing Value Columns:")
        for col, count in missing.head(10).items():
            pct = count / len(df) * 100
            print(f"    {col}: {count:,} ({pct:.1f}%)")
    
    # Target variable info (try common label columns)
    for label_col in ['Label', 'label', 'attack_cat', 'Attack', 'class']:
        if label_col in df.columns:
            print(f"\n  Target Variable: '{label_col}'")
            value_counts = df[label_col].value_counts()
            info["target_column"] = label_col
            info["num_classes"] = len(value_counts)
            print(f"  Classes: {len(value_counts)}")
            for val, count in value_counts.head(15).items():
                pct = count / len(df) * 100
                print(f"    {val}: {count:,} ({pct:.1f}%)")
            break
    
    print(f"{'='*60}\n")
    return info


if __name__ == "__main__":
    print("🛡️  IDS Data Loader")
    print("Use download_cicids2017() or download_unsw_nb15() to download datasets.")
    print("Use load_cicids2017() or load_unsw_nb15() to load datasets.")
