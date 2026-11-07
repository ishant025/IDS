"""
IDS Project - XGBoost Model
==============================
XGBoost Classifier for intrusion detection.
Fast, accurate, and handles imbalanced data well.
"""

from xgboost import XGBClassifier
from sklearn.model_selection import RandomizedSearchCV
import numpy as np


def create_model(n_estimators=200, max_depth=8, learning_rate=0.1, random_state=42, num_classes=2, **kwargs):
    """Create an XGBoost classifier."""
    objective = 'binary:logistic' if num_classes == 2 else 'multi:softprob'
    
    return XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        objective=objective,
        eval_metric='mlogloss',
        use_label_encoder=False,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        random_state=random_state,
        n_jobs=-1,
        verbosity=0,
        **kwargs
    )


def tune_model(X_train, y_train, n_iter=15, cv=3, random_state=42):
    """
    Hyperparameter tuning for XGBoost.
    
    Returns:
        Tuple of (best_model, best_params, best_score)
    """
    num_classes = len(np.unique(y_train))
    objective = 'binary:logistic' if num_classes == 2 else 'multi:softprob'
    
    param_distributions = {
        'n_estimators': [100, 200, 300, 500],
        'max_depth': [4, 6, 8, 10, 12],
        'learning_rate': [0.01, 0.05, 0.1, 0.2],
        'subsample': [0.6, 0.7, 0.8, 0.9],
        'colsample_bytree': [0.6, 0.7, 0.8, 0.9],
        'min_child_weight': [1, 3, 5, 7],
    }
    
    xgb = XGBClassifier(
        objective=objective,
        eval_metric='mlogloss',
        use_label_encoder=False,
        random_state=random_state,
        n_jobs=-1,
        verbosity=0
    )
    
    search = RandomizedSearchCV(
        xgb,
        param_distributions=param_distributions,
        n_iter=n_iter,
        cv=cv,
        scoring='f1_weighted',
        random_state=random_state,
        n_jobs=-1,
        verbose=1
    )
    
    search.fit(X_train, y_train)
    
    print(f"   🏆 Best F1-Score: {search.best_score_:.4f}")
    print(f"   📋 Best Params: {search.best_params_}")
    
    return search.best_estimator_, search.best_params_, search.best_score_


MODEL_NAME = "XGBoost"
MODEL_TYPE = "sklearn"  # XGBoost has sklearn-compatible API
