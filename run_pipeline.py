"""
🛡️ IDS - Master Pipeline Script
==================================
One-click script to run the entire pipeline:
1. Download dataset
2. Preprocess data
3. Train all models
4. Evaluate & generate reports
5. Launch dashboard

Usage:
    source venv/bin/activate
    python run_pipeline.py
"""

import sys
import os
import warnings
warnings.filterwarnings('ignore')

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    print("\n" + "🛡️"*20)
    print("  INTRUSION DETECTION SYSTEM — FULL PIPELINE")
    print("🛡️"*20 + "\n")
    
    # ================================================
    # STEP 1: Download Dataset
    # ================================================
    print("\n" + "="*60)
    print("📥 STEP 1: Downloading Dataset")
    print("="*60)
    
    from src.data_loader import download_cicids2017, load_cicids2017, dataset_info
    
    # download_cicids2017()  # Skipped as manually downloaded

    
    # ================================================
    # STEP 2: Load & Inspect
    # ================================================
    print("\n" + "="*60)
    print("📂 STEP 2: Loading Dataset")
    print("="*60)
    
    # Use sample for faster processing (adjust as needed)
    df = load_cicids2017(sample_frac=0.3)  # 30% sample for speed
    info = dataset_info(df, "CIC-IDS2017")
    
    # ================================================
    # STEP 3: Preprocess
    # ================================================
    print("\n" + "="*60)
    print("🔄 STEP 3: Preprocessing")
    print("="*60)
    
    from src.preprocessor import IDSPreprocessor
    
    preprocessor = IDSPreprocessor()
    target_col = info.get('target_column', 'Label')
    
    data, prep = preprocessor.preprocess(
        df,
        target_col=target_col,
        binary=True,  # Binary classification: Normal vs Attack
        test_size=0.2,
        val_size=0.1,
        save=True
    )
    
    print(f"\n📊 Data shapes:")
    print(f"   X_train: {data['X_train'].shape}")
    print(f"   X_val:   {data['X_val'].shape}")
    print(f"   X_test:  {data['X_test'].shape}")
    
    # ================================================
    # STEP 4: Train Models
    # ================================================
    print("\n" + "="*60)
    print("🤖 STEP 4: Training Models")
    print("="*60)
    
    from src.trainer import Trainer
    
    trainer = Trainer()
    trainer.train_all(
        data['X_train'], data['y_train'],
        X_val=data['X_val'], y_val=data['y_val'],
        tune=False,  # Set to True for hyperparameter tuning (slower)
    )
    trainer.save_models()
    
    # ================================================
    # STEP 5: Evaluate
    # ================================================
    print("\n" + "="*60)
    print("📊 STEP 5: Evaluating Models")
    print("="*60)
    
    from src.evaluator import Evaluator
    
    evaluator = Evaluator(label_mapping=prep.label_mapping)
    
    for name, model in trainer.trained_models.items():
        evaluator.evaluate_model(name, model, data['X_test'], data['y_test'])
    
    evaluator.full_report(data['y_test'], trainer.training_times)
    
    # ================================================
    # DONE!
    # ================================================
    print("\n" + "🎉"*20)
    print("  ✅ PIPELINE COMPLETE!")
    print("🎉"*20)
    print("\n  To launch the dashboard:")
    print("  streamlit run dashboard/app.py")
    print()


if __name__ == "__main__":
    main()
