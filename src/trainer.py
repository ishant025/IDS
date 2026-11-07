"""
IDS Project - Unified Trainer
===============================
Train, evaluate, and save the XGBoost model through a single interface.
"""

import time
import joblib
import numpy as np
from pathlib import Path
from typing import Tuple, Optional

from src.models import xgboost_model

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


# Registry of available models
MODEL_REGISTRY = {
    'xgboost': xgboost_model,
}


class Trainer:
    """Unified training interface for the XGBoost model."""

    def __init__(self):
        self.trained_models = {}
        self.training_times = {}
        self.results = {}

    def train_model(
        self,
        model_name: str,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
        tune: bool = False,
        **kwargs
    ) -> object:
        """
        Train a single model.

        Args:
            model_name: Key from MODEL_REGISTRY
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (unused for XGBoost, kept for interface parity)
            y_val: Validation labels (unused for XGBoost, kept for interface parity)
            tune: Whether to run hyperparameter tuning
            **kwargs: Additional model-specific arguments

        Returns:
            Trained model instance
        """
        if model_name not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model_name}. Available: {list(MODEL_REGISTRY.keys())}")

        module = MODEL_REGISTRY[model_name]
        print(f"\n{'='*60}")
        print(f"🤖 Training: {module.MODEL_NAME}")
        print(f"{'='*60}")

        start_time = time.time()

        if tune:
            model, best_params, best_score = module.tune_model(X_train, y_train)
        else:
            num_classes = len(np.unique(y_train))
            model = module.create_model(num_classes=num_classes, **kwargs)
            print(f"   Training on {len(X_train):,} samples...")
            model.fit(X_train, y_train)

        elapsed = time.time() - start_time
        self.trained_models[model_name] = model
        self.training_times[model_name] = elapsed

        train_pred = model.predict(X_train)
        train_acc = (train_pred == y_train).mean()

        print(f"\n   ⏱️  Training Time: {elapsed:.1f}s")
        print(f"   📊 Train Accuracy: {train_acc:.4f}")

        return model

    def train_all(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
        tune: bool = False,
        skip_models: list = None
    ) -> dict:
        """
        Train all models in the registry.

        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data (unused, kept for interface parity)
            tune: Hyperparameter tuning
            skip_models: List of model names to skip

        Returns:
            dict of model_name → trained model
        """
        skip = skip_models or []

        print("\n" + "🟢"*30)
        print("🚀 TRAINING ALL MODELS")
        print("🟢"*30)

        for name in MODEL_REGISTRY:
            if name in skip:
                print(f"\n⏭️  Skipping {name}")
                continue

            self.train_model(
                name, X_train, y_train,
                X_val=X_val, y_val=y_val,
                tune=tune
            )

        # Summary
        print("\n" + "="*60)
        print("📊 TRAINING SUMMARY")
        print("="*60)
        print(f"{'Model':<25} {'Time (s)':<12} {'Status':<10}")
        print("-"*47)
        for name, t in self.training_times.items():
            print(f"{MODEL_REGISTRY[name].MODEL_NAME:<25} {t:<12.1f} {'✅':}")

        return self.trained_models

    def save_models(self, output_dir: str = None):
        """Save all trained models to disk."""
        if output_dir is None:
            output_dir = str(MODELS_DIR)

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        print("\n💾 Saving models...")
        for name, model in self.trained_models.items():
            path = Path(output_dir) / f"{name}.pkl"
            joblib.dump(model, str(path))
            print(f"   ✅ {name} → {path}")

        # Save training times
        joblib.dump(self.training_times, Path(output_dir) / "training_times.pkl")
        print("   ✅ Training times saved")

    def load_models(self, input_dir: str = None):
        """Load all saved models from disk."""
        if input_dir is None:
            input_dir = str(MODELS_DIR)

        print("\n📂 Loading models...")

        for name in MODEL_REGISTRY:
            path = Path(input_dir) / f"{name}.pkl"
            if path.exists():
                self.trained_models[name] = joblib.load(str(path))
                print(f"   ✅ Loaded {name} from {path}")

        # Load training times
        times_path = Path(input_dir) / "training_times.pkl"
        if times_path.exists():
            self.training_times = joblib.load(str(times_path))

        return self.trained_models
