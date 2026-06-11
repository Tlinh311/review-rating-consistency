(function initializeReviewApp(globalScope) {
    "use strict";

    const STATUS_VIEWS = {
        consistent: {
            label: "Consistent",
            className: "consistent",
            message: "Review text and rating are consistent within 1-star gap.",
        },
        potential_mismatch: {
            label: "Mismatch",
            className: "potential-mismatch",
            message: "Significant gap detected (2+ stars) between review text and rating.",
        },
        inconclusive: {
            label: "Inconclusive",
            className: "inconclusive",
            message: "Review text is too short or model score is below the uncertainty threshold.",
        },
    };

    const MODEL_LABELS = {
        weighted_logistic_regression: "Weighted Logistic Regression",
        unweighted_logistic_regression: "Unweighted Logistic Regression",
        linear_svm: "Linear SVM",
        complement_naive_bayes: "Complement Naive Bayes",
    };

    function getStatusView(status) {
        return STATUS_VIEWS[status] || STATUS_VIEWS.inconclusive;
    }

    function validateReview(text) {
        const trimmed = String(text || "").trim();
        if (!trimmed) {
            return "Please enter the review text.";
        }
        if (trimmed.length > 5000) {
            return "Review text must not exceed 5,000 characters.";
        }
        return "";
    }

    function formatPercent(value, digits) {
        return `${Number(value || 0).toFixed(digits)}%`;
    }

    function formatNumber(value) {
        return Number(value || 0).toLocaleString("vi-VN");
    }

    function formatMetric(value, digits) {
        return Number(value || 0).toFixed(digits);
    }

    async function readJsonResponse(response) {
        const data = await response.json();
        if (!response.ok) {
            const detail = typeof data.detail === "string"
                ? data.detail
                : "Server encountered an error while processing request.";
            throw new Error(detail);
        }
        return data;
    }

    function createElement(tagName, className, textContent) {
        const element = document.createElement(tagName);
        if (className) {
            element.className = className;
        }
        if (textContent !== undefined) {
            element.textContent = textContent;
        }
        return element;
    }

    function renderScoreBars(scores) {
        const container = document.getElementById("score-bars");
        container.replaceChildren();
        for (let rating = 1; rating <= 5; rating += 1) {
            const score = Number(scores[String(rating)] || 0);
            const row = createElement("div", "score-row");
            row.appendChild(createElement("span", "", `${rating}★`));

            const track = createElement("div", "score-track");
            const fill = createElement("div", "score-fill");
            fill.style.width = `${Math.max(0, Math.min(score, 100))}%`;
            track.appendChild(fill);
            row.appendChild(track);
            row.appendChild(
                createElement("strong", "", formatPercent(score, 1))
            );
            container.appendChild(row);
        }
    }

    function renderPrediction(result) {
        const view = getStatusView(result.status);
        document.getElementById("empty-result").classList.add("hidden");
        document.getElementById("result-content").classList.remove("hidden");

        const status = document.getElementById("result-status");
        status.textContent = view.label;
        status.className = `result-status ${view.className}`;
        document.getElementById("result-message").textContent = view.message;
        document.getElementById("actual-rating-result").textContent =
            String(result.actual_rating);
        document.getElementById("predicted-rating-result").textContent =
            String(result.predicted_rating);
        document.getElementById("rating-gap-result").textContent =
            String(result.rating_gap);
        document.getElementById("top-score-result").textContent =
            formatPercent(result.top_model_score, 1);
        document.getElementById("cleaned-text-result").textContent =
            result.cleaned_text;
        document.getElementById("token-count-result").textContent =
            `${result.token_count} tokens after preprocessing`;
        renderScoreBars(result.class_scores);
    }

    function renderDistribution(dataset) {
        const container = document.getElementById("distribution-chart");
        container.replaceChildren();
        const distribution = dataset.rating_distribution || {};
        const percentages = dataset.rating_percentages || {};
        const maximum = Object.values(distribution)
            .map(Number)
            .reduce((current, value) => Math.max(current, value), 1);

        for (let rating = 1; rating <= 5; rating += 1) {
            const key = String(rating);
            const count = Number(distribution[key] || 0);
            const percentage = Number(percentages[key] || 0);
            const row = createElement("div", "distribution-row");
            row.appendChild(createElement("span", "", `${rating}★`));

            const track = createElement("div", "distribution-track");
            const fill = createElement("div", "distribution-fill");
            fill.style.width = `${count / maximum * 100}%`;
            track.appendChild(fill);
            row.appendChild(track);
            row.appendChild(
                createElement(
                    "span",
                    "distribution-value",
                    `${formatNumber(count)} / ${formatPercent(percentage, 1)}`
                )
            );
            container.appendChild(row);
        }
    }

    function renderConfusionMatrix(matrix) {
        const container = document.getElementById("confusion-matrix");
        container.replaceChildren();
        const flatValues = matrix.flat().map(Number);
        const maximum = flatValues.reduce(
            (current, value) => Math.max(current, value),
            1
        );
        container.appendChild(createElement("div", "matrix-cell matrix-label", ""));

        for (let label = 1; label <= 5; label += 1) {
            container.appendChild(
                createElement("div", "matrix-cell matrix-label", `Pred ${label}`)
            );
        }

        matrix.forEach((row, rowIndex) => {
            container.appendChild(
                createElement(
                    "div",
                    "matrix-cell matrix-label",
                    `Actual ${rowIndex + 1}`
                )
            );
            row.forEach((value) => {
                const cell = createElement(
                    "div",
                    "matrix-cell",
                    formatNumber(value)
                );
                const opacity = 0.08 + Number(value) / maximum * 0.56;
                cell.style.setProperty("--matrix-opacity", opacity.toFixed(3));
                container.appendChild(cell);
            });
        });
    }

    function renderComparison(rows) {
        const body = document.getElementById("comparison-table");
        body.replaceChildren();
        rows.forEach((row) => {
            const tableRow = document.createElement("tr");
            tableRow.appendChild(
                createElement(
                    "td",
                    "",
                    MODEL_LABELS[row.name] || row.name
                )
            );
            tableRow.appendChild(
                createElement("td", "", formatPercent(row.accuracy * 100, 2))
            );
            tableRow.appendChild(
                createElement("td", "", formatMetric(row.macro_f1, 4))
            );
            tableRow.appendChild(
                createElement("td", "", formatMetric(row.mae, 4))
            );
            body.appendChild(tableRow);
        });
    }

    function renderStats(payload) {
        const dataset = payload.dataset;
        const metrics = payload.model.holdout_metrics;
        document.getElementById("total-raw").textContent =
            formatNumber(dataset.total_raw);
        document.getElementById("total-clean").textContent =
            formatNumber(dataset.total_clean);
        document.getElementById("duplicates-removed").textContent =
            formatNumber(dataset.duplicate_pairs_removed);
        document.getElementById("empty-reviews").textContent =
            formatNumber(dataset.empty_after_cleaning);
        document.getElementById("macro-f1").textContent =
            formatMetric(metrics.macro_f1, 4);
        document.getElementById("mae").textContent =
            formatMetric(metrics.mae, 4);
        document.getElementById("within-one").textContent =
            formatPercent(metrics.within_one_star * 100, 2);
        document.getElementById("recall-two").textContent =
            formatPercent(metrics.recall_per_class["2"] * 100, 2);

        const trainedDate = new Date(payload.model.created_at);
        document.getElementById("model-trained-at").textContent =
            `Model trained at ${trainedDate.toLocaleString("en-US")}`;

        renderDistribution(dataset);
        renderConfusionMatrix(metrics.confusion_matrix);
        renderComparison(payload.model.comparison || []);
    }

    async function loadHealth() {
        const status = document.getElementById("system-status");
        const text = document.getElementById("system-status-text");
        if (!status || !text) {
            return;
        }
        try {
            const response = await fetch("/api/health");
            const data = await readJsonResponse(response);
            status.className = "system-status ready";
            text.textContent = `Model ready / sklearn ${data.scikit_learn_runtime}`;
        } catch (error) {
            status.className = "system-status error";
            text.textContent = "Model unavailable";
        }
    }

    async function loadStats() {
        try {
            const response = await fetch("/api/stats");
            renderStats(await readJsonResponse(response));
        } catch (error) {
            document.getElementById("model-trained-at").textContent =
                "Failed to load statistics";
        }
    }

    async function submitReview(event) {
        event.preventDefault();
        const reviewInput = document.getElementById("review-text");
        const errorBox = document.getElementById("form-error");
        const submitButton = document.getElementById("submit-button");
        const validationError = validateReview(reviewInput.value);
        errorBox.textContent = validationError;
        if (validationError) {
            reviewInput.focus();
            return;
        }

        const ratingInput = document.querySelector(
            'input[name="actual_rating"]:checked'
        );
        submitButton.disabled = true;
        submitButton.textContent = "Analyzing...";

        try {
            const response = await fetch("/api/predict", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    review_text: reviewInput.value,
                    actual_rating: Number(ratingInput.value),
                }),
            });
            renderPrediction(await readJsonResponse(response));
        } catch (error) {
            errorBox.textContent = error.message;
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Analyze Review";
        }
    }

    function updateCharacterCount() {
        const reviewInput = document.getElementById("review-text");
        document.getElementById("character-count").textContent =
            `${reviewInput.value.length} / 5000`;
    }

    async function fillExample(button) {
        const type = button.dataset.exampleType;
        if (!type) {
            return;
        }

        const reviewInput = document.getElementById("review-text");
        const errorBox = document.getElementById("form-error");

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = "Loading...";

        try {
            const response = await fetch(`/api/random-example?type=${type}`);
            const data = await readJsonResponse(response);

            reviewInput.value = data.review;
            const rating = document.querySelector(
                `input[name="actual_rating"][value="${data.rating}"]`
            );
            if (rating) {
                rating.checked = true;
            }
            errorBox.textContent = "";
            updateCharacterCount();
            reviewInput.focus();
        } catch (error) {
            errorBox.textContent = `Failed to fetch example: ${error.message}`;
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    function bindBrowserEvents() {
        const form = document.getElementById("predict-form");
        if (!form) {
            return;
        }
        form.addEventListener("submit", submitReview);
        document.getElementById("review-text").addEventListener(
            "input",
            updateCharacterCount
        );
        document.querySelectorAll(".example-button").forEach((button) => {
            button.addEventListener("click", () => fillExample(button));
        });
        loadHealth();
        loadStats();
    }

    const publicApi = {
        getStatusView,
        validateReview,
        formatPercent,
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = publicApi;
    }
    globalScope.ReviewConsistencyApp = publicApi;

    if (typeof document !== "undefined") {
        document.addEventListener("DOMContentLoaded", bindBrowserEvents);
    }
}(typeof window !== "undefined" ? window : globalThis));
