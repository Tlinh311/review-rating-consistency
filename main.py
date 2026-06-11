from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import pandas as pd
import sklearn
import uvicorn
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse, JSONResponse
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from src.config import DEFAULT_DATA_PATH
from src.predict import (
    DEFAULT_METADATA_PATH,
    DEFAULT_MODEL_PATH,
    ModelResourceError,
    ReviewValidationError,
    load_resources,
    predict_single_review,
)
from src.preprocessing import prepare_dataset


PROJECT_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PROJECT_ROOT / "static"


class ReviewInput(BaseModel):
    review_text: str = Field(min_length=1, max_length=5000)
    actual_rating: int = Field(ge=1, le=5)
    model_name: Literal[
        "production",
        "logistic_regression",
        "review_rating_logistic_regression",
    ] | None = None


def build_stats_payload(
    data_path: Path,
    metadata: dict,
) -> dict:
    raw_df = pd.read_csv(data_path)
    _, data_report = prepare_dataset(raw_df)
    return {
        "dataset": data_report,
        "model": {
            "name": metadata["model_name"],
            "created_at": metadata["created_at"],
            "holdout_metrics": metadata["holdout_metrics"],
            "uncertainty_threshold": metadata["uncertainty_threshold"],
            "comparison": metadata["model_comparison"],
        },
    }


def create_app(
    model_path: Path = DEFAULT_MODEL_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
    data_path: Path = DEFAULT_DATA_PATH,
) -> FastAPI:
    model_path = Path(model_path)
    metadata_path = Path(metadata_path)
    data_path = Path(data_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pipeline = None
        app.state.metadata = None
        app.state.stats = None
        app.state.resource_error = None
        app.state.stats_error = None
        app.state.reviews_df = None

        try:
            pipeline, metadata = load_resources(
                model_path=model_path,
                metadata_path=metadata_path,
            )
            app.state.pipeline = pipeline
            app.state.metadata = metadata
        except (ModelResourceError, OSError, ValueError) as error:
            app.state.resource_error = str(error)

        if app.state.metadata is not None:
            try:
                app.state.stats = build_stats_payload(
                    data_path,
                    app.state.metadata,
                )
            except (OSError, ValueError, pd.errors.ParserError) as error:
                app.state.stats_error = str(error)

        try:
            if data_path.exists():
                df = pd.read_csv(data_path)
                if "Review" in df.columns and "Rating" in df.columns:
                    df = df[["Review", "Rating"]].dropna()
                    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
                    app.state.reviews_df = df.dropna()
        except Exception:
            pass

        yield

    application = FastAPI(
        title="Review Consistency Analysis API",
        description=(
            "Predict ratings from English reviews and assess "
            "consistency with user ratings."
        ),
        version="2.0.0",
        lifespan=lifespan,
    )

    @application.get("/")
    def read_root():
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Web interface not found.",
            )
        return FileResponse(index_path)

    @application.post("/api/predict")
    def predict_review(data: ReviewInput):
        if application.state.pipeline is None:
            raise HTTPException(
                status_code=503,
                detail=application.state.resource_error
                or "Model not ready.",
            )

        try:
            return predict_single_review(
                review_text=data.review_text,
                actual_rating=data.actual_rating,
                model_name=data.model_name,
                pipeline=application.state.pipeline,
                metadata=application.state.metadata,
            )
        except ReviewValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @application.get("/api/random-example")
    def get_random_example(type: Literal["positive", "neutral", "contradictory"]):
        import random

        if application.state.reviews_df is None:
            fallbacks = {
                "positive": [
                    {"rating": 5, "review": "The food was excellent and the service was friendly."},
                    {"rating": 5, "review": "Absolutely amazing experience! The staff went above and beyond, and the steak was cooked to perfection."}
                ],
                "neutral": [
                    {"rating": 3, "review": "The food was acceptable but the service was slow."},
                    {"rating": 3, "review": "Average restaurant. The appetizers were good, but the main course was quite disappointing."}
                ],
                "contradictory": [
                    {"rating": 5, "review": "Terrible cold food and rude service."},
                    {"rating": 5, "review": "The worst dining experience of my life. I will never return."}
                ]
            }
            return random.choice(fallbacks[type])

        df = application.state.reviews_df
        try:
            if type == "positive":
                subset = df[df["Rating"] == 5]
                if subset.empty:
                    subset = df[df["Rating"] >= 4]
                row = subset.sample(n=1).iloc[0]
                return {"rating": int(row["Rating"]), "review": str(row["Review"])}
            elif type == "neutral":
                subset = df[df["Rating"] == 3]
                if subset.empty:
                    subset = df
                row = subset.sample(n=1).iloc[0]
                return {"rating": int(row["Rating"]), "review": str(row["Review"])}
            elif type == "contradictory":
                if random.random() < 0.5:
                    subset = df[df["Rating"] == 1]
                    if subset.empty:
                        subset = df[df["Rating"] <= 2]
                    row = subset.sample(n=1).iloc[0]
                    return {"rating": 5, "review": str(row["Review"])}
                else:
                    subset = df[df["Rating"] == 5]
                    if subset.empty:
                        subset = df[df["Rating"] >= 4]
                    row = subset.sample(n=1).iloc[0]
                    return {"rating": 1, "review": str(row["Review"])}
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Cannot generate sample data: {str(error)}"
            )


    @application.get("/api/stats")
    def get_dataset_stats():
        if application.state.stats is None:
            raise HTTPException(
                status_code=503,
                detail=application.state.stats_error
                or application.state.resource_error
                or "Statistics not ready.",
            )
        return application.state.stats

    @application.get("/api/model-info")
    def get_model_info():
        metadata = application.state.metadata
        if metadata is None:
            raise HTTPException(
                status_code=503,
                detail=application.state.resource_error
                or "Model metadata not ready.",
            )
        return {
            "model_name": metadata["model_name"],
            "created_at": metadata["created_at"],
            "features": metadata["features"],
            "selected_parameters": metadata["selected_parameters"],
            "class_weights": metadata["class_weights"],
            "uncertainty_threshold": metadata["uncertainty_threshold"],
            "holdout_metrics": metadata["holdout_metrics"],
            "limitations": metadata["limitations"],
        }

    @application.get("/api/health")
    def get_health():
        metadata = application.state.metadata
        if application.state.pipeline is None or metadata is None:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "model_loaded": False,
                    "scikit_learn_runtime": sklearn.__version__,
                    "detail": application.state.resource_error
                    or "Model not ready.",
                },
            )
        return {
            "status": "ready",
            "model_loaded": True,
            "model_name": metadata["model_name"],
            "scikit_learn_runtime": sklearn.__version__,
            "scikit_learn_trained": metadata["libraries"]["scikit_learn"],
        }

    application.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )
    return application


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
