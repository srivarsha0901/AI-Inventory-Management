# FreshTrack ML Pipeline
# This module is imported by the Flask backend (backend/routes/ml_routes.py)
# It is NOT a standalone Flask app.
#
# Pipeline:
#   1. ml/01_preprocess.py  — Preprocess Kaggle Favorita data
#   2. ml/02_train_models.py — Train & compare 6 models, save best
#   3. ml/03_daily_predict.py — Batch predict on processed data
#   4. ml/predict_for_store.py — Per-store prediction (called by backend)
#
# The trained model (models/best_model.pkl) is loaded by predict_for_store.py
# and used to generate 7-day demand forecasts for any store's products.
