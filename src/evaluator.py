"""
IDS Project - Model Evaluator
================================
Comprehensive evaluation: metrics, confusion matrices, ROC curves, comparison.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    roc_curve, auc
)
from sklearn.preprocessing import label_binarize
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"


class Evaluator:
    """Comprehensive model evaluation and comparison."""
    
    def __init__(self, label_mapping: dict = None):
        self.label_mapping = label_mapping or {}
        self.results = {}
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    
    def evaluate_model(
        self,
        model_name: str,
        model,
        X_test: np.ndarray,
        y_test: np.ndarray,
        is_pytorch: bool = False
    ) -> dict:
        """
        Evaluate a single model with all metrics.
        
        Returns:
            dict with all metric scores
        """
        print(f"\n📊 Evaluating: {model_name}")
        print("-" * 40)
        
        # Predictions
        y_pred = model.predict(X_test)
        
        # Probabilities (for ROC)
        try:
            if is_pytorch:
                y_prob = model.predict_proba(X_test)
            elif hasattr(model, 'predict_proba'):
                y_prob = model.predict_proba(X_test)
            else:
                y_prob = None
        except Exception:
            y_prob = None
        
        # Core metrics
        num_classes = len(np.unique(y_test))
        average = 'binary' if num_classes == 2 else 'weighted'
        
        metrics = {
            'model_name': model_name,
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average=average, zero_division=0),
            'recall': recall_score(y_test, y_pred, average=average, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, average=average, zero_division=0),
        }
        
        # ROC-AUC
        if y_prob is not None:
            try:
                if num_classes == 2:
                    metrics['roc_auc'] = roc_auc_score(y_test, y_prob[:, 1])
                else:
                    y_test_bin = label_binarize(y_test, classes=np.unique(y_test))
                    metrics['roc_auc'] = roc_auc_score(
                        y_test_bin, y_prob, average='weighted', multi_class='ovr'
                    )
            except Exception as e:
                metrics['roc_auc'] = None
                print(f"   ⚠️  ROC-AUC calculation failed: {e}")
        else:
            metrics['roc_auc'] = None
        
        # Store predictions for later use
        metrics['y_pred'] = y_pred
        metrics['y_prob'] = y_prob
        
        self.results[model_name] = metrics
        
        # Print metrics
        print(f"   Accuracy:  {metrics['accuracy']:.4f}")
        print(f"   Precision: {metrics['precision']:.4f}")
        print(f"   Recall:    {metrics['recall']:.4f}")
        print(f"   F1-Score:  {metrics['f1_score']:.4f}")
        if metrics['roc_auc']:
            print(f"   ROC-AUC:   {metrics['roc_auc']:.4f}")
        
        return metrics
    
    def comparison_table(self, training_times: dict = None) -> pd.DataFrame:
        """Create a side-by-side model comparison table."""
        rows = []
        for name, metrics in self.results.items():
            row = {
                'Model': name,
                'Accuracy': f"{metrics['accuracy']:.4f}",
                'Precision': f"{metrics['precision']:.4f}",
                'Recall': f"{metrics['recall']:.4f}",
                'F1-Score': f"{metrics['f1_score']:.4f}",
                'ROC-AUC': f"{metrics['roc_auc']:.4f}" if metrics.get('roc_auc') else 'N/A',
            }
            if training_times and name in training_times:
                row['Train Time (s)'] = f"{training_times[name]:.1f}"
            rows.append(row)
        
        df = pd.DataFrame(rows)
        print("\n" + "="*80)
        print("📊 MODEL COMPARISON TABLE")
        print("="*80)
        print(df.to_string(index=False))
        print("="*80)
        
        return df
    
    def plot_confusion_matrices(
        self,
        y_test: np.ndarray,
        figsize: tuple = (20, 5),
        save_path: str = None
    ):
        """Plot confusion matrices for all models side by side."""
        n_models = len(self.results)
        fig, axes = plt.subplots(1, n_models, figsize=figsize)
        
        if n_models == 1:
            axes = [axes]
        
        class_names = [self.label_mapping.get(i, str(i)) for i in sorted(self.label_mapping.keys())]
        if not class_names:
            class_names = [str(i) for i in sorted(np.unique(y_test))]
        
        for ax, (name, metrics) in zip(axes, self.results.items()):
            cm = confusion_matrix(y_test, metrics['y_pred'])
            
            # Normalize
            cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            
            sns.heatmap(
                cm_normalized, annot=True, fmt='.2%',
                cmap='Blues', ax=ax,
                xticklabels=class_names[:cm.shape[0]],
                yticklabels=class_names[:cm.shape[0]],
                square=True, linewidths=0.5
            )
            ax.set_title(f'{name}', fontsize=12, fontweight='bold')
            ax.set_ylabel('True Label')
            ax.set_xlabel('Predicted Label')
        
        plt.suptitle('🔍 Confusion Matrices (Normalized)', fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path is None:
            save_path = str(FIGURES_DIR / "confusion_matrices.png")
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()
        print(f"   💾 Saved to: {save_path}")
    
    def plot_roc_curves(
        self,
        y_test: np.ndarray,
        figsize: tuple = (10, 8),
        save_path: str = None
    ):
        """Plot ROC curves for all models on one graph."""
        fig, ax = plt.subplots(figsize=figsize)
        
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12']
        
        for i, (name, metrics) in enumerate(self.results.items()):
            y_prob = metrics.get('y_prob')
            if y_prob is None:
                continue
            
            num_classes = len(np.unique(y_test))
            
            if num_classes == 2:
                fpr, tpr, _ = roc_curve(y_test, y_prob[:, 1])
                roc_auc_val = auc(fpr, tpr)
                ax.plot(fpr, tpr, color=colors[i % len(colors)], lw=2,
                       label=f'{name} (AUC={roc_auc_val:.4f})')
            else:
                # Macro-average ROC for multi-class
                y_test_bin = label_binarize(y_test, classes=np.unique(y_test))
                n_classes = y_test_bin.shape[1]
                
                fpr_micro, tpr_micro, _ = roc_curve(
                    y_test_bin.ravel(), y_prob[:, :n_classes].ravel()
                )
                roc_auc_val = auc(fpr_micro, tpr_micro)
                ax.plot(fpr_micro, tpr_micro, color=colors[i % len(colors)], lw=2,
                       label=f'{name} (micro-avg AUC={roc_auc_val:.4f})')
        
        # Diagonal
        ax.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.5, label='Random (AUC=0.5)')
        
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('False Positive Rate', fontsize=12)
        ax.set_ylabel('True Positive Rate', fontsize=12)
        ax.set_title('📈 ROC Curves — Model Comparison', fontsize=14, fontweight='bold')
        ax.legend(loc='lower right', fontsize=10)
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = str(FIGURES_DIR / "roc_curves.png")
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()
        print(f"   💾 Saved to: {save_path}")
    
    def plot_metrics_comparison(
        self,
        figsize: tuple = (12, 6),
        save_path: str = None
    ):
        """Plot bar chart comparing all metrics across models."""
        metrics_to_plot = ['accuracy', 'precision', 'recall', 'f1_score']
        model_names = list(self.results.keys())
        
        x = np.arange(len(model_names))
        width = 0.18
        
        fig, ax = plt.subplots(figsize=figsize)
        colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12']
        
        for i, metric in enumerate(metrics_to_plot):
            values = [self.results[name][metric] for name in model_names]
            bars = ax.bar(x + i * width, values, width, label=metric.replace('_', ' ').title(),
                         color=colors[i], alpha=0.85, edgecolor='white')
            
            # Value labels on bars
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.005,
                       f'{val:.3f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
        
        ax.set_ylabel('Score', fontsize=12)
        ax.set_title('🏆 Model Performance Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels(model_names, fontsize=11)
        ax.legend(fontsize=10)
        ax.set_ylim(0, 1.1)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = str(FIGURES_DIR / "metrics_comparison.png")
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()
        print(f"   💾 Saved to: {save_path}")
    
    def get_best_model(self, metric: str = 'f1_score') -> str:
        """Get the name of the best performing model by a given metric."""
        best_name = max(
            self.results,
            key=lambda x: self.results[x].get(metric, 0) or 0
        )
        best_score = self.results[best_name][metric]
        print(f"\n🏆 Best Model (by {metric}): {best_name} = {best_score:.4f}")
        return best_name
    
    def full_report(
        self,
        y_test: np.ndarray,
        training_times: dict = None,
        save_dir: str = None
    ):
        """Generate complete evaluation report with all visualizations."""
        if save_dir is None:
            save_dir = str(FIGURES_DIR)
        
        print("\n" + "🔵"*30)
        print("📊 FULL EVALUATION REPORT")
        print("🔵"*30)
        
        # 1. Comparison table
        comparison_df = self.comparison_table(training_times)
        comparison_df.to_csv(Path(save_dir) / "model_comparison.csv", index=False)
        
        # 2. Confusion matrices
        self.plot_confusion_matrices(y_test)
        
        # 3. ROC curves
        self.plot_roc_curves(y_test)
        
        # 4. Metrics comparison bar chart
        self.plot_metrics_comparison()
        
        # 5. Best model
        best = self.get_best_model('f1_score')
        
        print(f"\n✅ Full report generated in: {save_dir}")
        return comparison_df
