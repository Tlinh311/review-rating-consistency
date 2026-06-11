from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "restaurant_reviews.csv"
DEFAULT_MODELS_DIR = PROJECT_ROOT / "models"
MODEL_FILENAME = "review_rating_pipeline.joblib"
METADATA_FILENAME = "model_metadata.json"
DEFAULT_MODEL_PATH = DEFAULT_MODELS_DIR / MODEL_FILENAME
DEFAULT_METADATA_PATH = DEFAULT_MODELS_DIR / METADATA_FILENAME
