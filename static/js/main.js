(function initializeReviewApp(globalScope) {
    "use strict";

    const TRANSLATIONS = {
        en: {
            "header.status_checking": "Checking model status...",
            "hero.eyebrow": "Predict Rating from English Text",
            "hero.title": "Review Consistency Checker",
            "hero.description": "The model predicts rating from 1 to 5 based on English review content and compares it with the actual user rating to detect inconsistencies.",
            "scope.label": "Scope & Limitations",
            "scope.text": "The model only analyzes the consistency between the English review content and the selected rating. The results are not intended to conclude that a review is fake.",
            "analysis.title": "Analyze Single Review",
            "analysis.max_chars": "Max 5,000 characters",
            "analysis.quick_fill": "Quick Fill:",
            "analysis.positive": "Consistent Positive",
            "analysis.neutral": "Consistent Neutral",
            "analysis.contradictory": "Contradictory",
            "form.label": "Review Text",
            "form.placeholder": "Write an English restaurant review...",
            "form.legend": "Actual Rating",
            "form.submit": "Analyze Review",
            "result.title": "Analysis Result",
            "result.empty_text": "Analysis results will display predicted rating, gap, confidence scores, and consistency status.",
            "result.label_actual": "Actual Rating",
            "result.label_predicted": "Predicted Rating",
            "result.label_gap": "Rating Gap",
            "result.label_top_score": "Top Model Score",
            "result.score_title": "Model Score by Rating",
            "result.score_subtitle": "Uncalibrated probability scores",
            "result.details_summary": "Preprocessed Review Text",
            "dashboard.title": "Dataset & Model Quality",
            "dashboard.stats_raw": "Original Rows",
            "dashboard.stats_clean": "Training Rows",
            "dashboard.stats_duplicates": "Duplicates Removed",
            "dashboard.stats_empty": "Empty Reviews",
            "dashboard.dist_title": "Rating Distribution (Cleaned)",
            "dashboard.dist_subtitle": "5-star class remains the majority",
            "dashboard.perf_title": "Holdout Performance",
            "dashboard.perf_subtitle": "Optimized for Macro-F1 & Rating MAE",
            "dashboard.perf_within_one": "Within 1-Star Error",
            "dashboard.perf_recall_two": "Recall (2-Star Class)",
            "dashboard.matrix_title": "Confusion Matrix",
            "dashboard.matrix_subtitle": "Rows represent actual ratings, columns represent predicted ratings",
            "dashboard.compare_title": "Baseline Comparison",
            "dashboard.compare_subtitle": "Cross-validation results on the training set",
            "dashboard.table_model": "Model",
            "dashboard.table_accuracy": "Accuracy",
            "dashboard.table_macro_f1": "Macro-F1",
            "dashboard.table_mae": "MAE"
        },
        vi: {
            "header.status_checking": "Đang kiểm tra trạng thái model...",
            "hero.eyebrow": "Dự đoán rating từ văn bản tiếng Anh",
            "hero.title": "Đánh Giá Độ Nhất Quán Review",
            "hero.description": "Mô hình dự đoán rating từ 1 đến 5 dựa trên nội dung review tiếng Anh và so sánh với rating thực tế của người dùng để phát hiện các trường hợp không nhất quán.",
            "scope.label": "Phạm vi & Giới hạn",
            "scope.text": "Mô hình chỉ phân tích độ nhất quán giữa nội dung review tiếng Anh và rating được chọn. Kết quả không dùng để kết luận một review là giả mạo.",
            "analysis.title": "Phân Tích Review Đơn Lẻ",
            "analysis.max_chars": "Tối đa 5.000 ký tự",
            "analysis.quick_fill": "Điền nhanh:",
            "analysis.positive": "Tích cực nhất quán",
            "analysis.neutral": "Trung lập nhất quán",
            "analysis.contradictory": "Mâu thuẫn",
            "form.label": "Nội dung review",
            "form.placeholder": "Viết review nhà hàng bằng tiếng Anh...",
            "form.legend": "Rating thực tế",
            "form.submit": "Phân tích review",
            "result.title": "Kết quả phân tích",
            "result.empty_text": "Kết quả phân tích sẽ hiển thị rating dự đoán, độ chênh lệch, độ tin cậy và trạng thái nhất quán.",
            "result.label_actual": "Rating thực tế",
            "result.label_predicted": "Rating dự đoán",
            "result.label_gap": "Chênh lệch rating",
            "result.label_top_score": "Điểm mô hình cao nhất",
            "result.score_title": "Điểm mô hình theo rating",
            "result.score_subtitle": "Điểm xác suất chưa hiệu chuẩn",
            "result.details_summary": "Nội dung review sau tiền xử lý",
            "dashboard.title": "Bộ dữ liệu & Chất lượng mô hình",
            "dashboard.stats_raw": "Dữ liệu gốc",
            "dashboard.stats_clean": "Dữ liệu huấn luyện",
            "dashboard.stats_duplicates": "Trùng lặp đã loại bỏ",
            "dashboard.stats_empty": "Review rỗng",
            "dashboard.dist_title": "Phân bổ rating (Đã làm sạch)",
            "dashboard.dist_subtitle": "Lớp 5 sao tiếp tục chiếm đa số",
            "dashboard.perf_title": "Hiệu năng Holdout",
            "dashboard.perf_subtitle": "Tối ưu hóa cho Macro-F1 & Rating MAE",
            "dashboard.perf_within_one": "Sai lệch trong khoảng 1 sao",
            "dashboard.perf_recall_two": "Recall (Lớp 2 sao)",
            "dashboard.matrix_title": "Ma trận nhầm lẫn",
            "dashboard.matrix_subtitle": "Các hàng đại diện cho rating thực tế, các cột đại diện cho rating dự đoán",
            "dashboard.compare_title": "So sánh với Baseline",
            "dashboard.compare_subtitle": "Kết quả cross-validation trên tập huấn luyện",
            "dashboard.table_model": "Mô hình",
            "dashboard.table_accuracy": "Độ chính xác",
            "dashboard.table_macro_f1": "Macro-F1",
            "dashboard.table_mae": "MAE"
        }
    };

    const ERROR_TRANSLATIONS = {
        en: {
            required: "Please enter the review text.",
            too_long: "Review text must not exceed 5,000 characters.",
            api_fallback: "Server encountered an error while processing request.",
            example_failed: "Failed to fetch example: ",
            stats_failed: "Failed to load statistics"
        },
        vi: {
            required: "Vui lòng nhập nội dung review.",
            too_long: "Nội dung review không được vượt quá 5.000 ký tự.",
            api_fallback: "Hệ thống gặp lỗi trong quá trình xử lý yêu cầu.",
            example_failed: "Không thể lấy dữ liệu mẫu: ",
            stats_failed: "Không thể tải dữ liệu thống kê"
        }
    };

    const STATUS_VIEWS = {
        consistent: {
            className: "consistent",
            en: {
                label: "Consistent",
                message: "Review text and rating are consistent within 1-star gap."
            },
            vi: {
                label: "Nhất quán",
                message: "Nội dung review và rating nhất quán trong khoảng sai lệch 1 sao."
            }
        },
        potential_mismatch: {
            className: "potential-mismatch",
            en: {
                label: "Mismatch",
                message: "Significant gap detected (2+ stars) between review text and rating."
            },
            vi: {
                label: "Không nhất quán",
                message: "Phát hiện khoảng cách lớn (từ 2 sao trở lên) giữa nội dung review và rating."
            }
        },
        inconclusive: {
            className: "inconclusive",
            en: {
                label: "Inconclusive",
                message: "Review text is too short or model score is below the uncertainty threshold."
            },
            vi: {
                label: "Không thể kết luận",
                message: "Nội dung review quá ngắn hoặc điểm mô hình dưới ngưỡng tin cậy."
            }
        }
    };

    const MODEL_LABELS = {
        weighted_logistic_regression: "Weighted Logistic Regression",
        unweighted_logistic_regression: "Unweighted Logistic Regression",
        linear_svm: "Linear SVM",
        complement_naive_bayes: "Complement Naive Bayes",
    };

    const appState = {
        healthData: null,
        statsData: null,
        lastResult: null
    };

    let currentLanguage = "en";
    if (typeof localStorage !== "undefined") {
        currentLanguage = localStorage.getItem("preferredLanguage") || "en";
        if (currentLanguage !== "en" && currentLanguage !== "vi") {
            currentLanguage = "en";
        }
    }

    function translateError(msg, lang) {
        if (lang === "en") return msg;
        const mapping = {
            "Review has no valid English words after preprocessing.": "Review không còn từ tiếng Anh hợp lệ sau tiền xử lý.",
            "Rating must be between 1 and 5.": "Rating phải nằm trong khoảng từ 1 đến 5.",
            "Model not ready.": "Model chưa sẵn sàng.",
            "Statistics not ready.": "Thống kê chưa sẵn sàng.",
            "Model metadata not ready.": "Model metadata chưa sẵn sàng.",
            "Web interface not found.": "Không tìm thấy giao diện web."
        };
        return mapping[msg] || msg;
    }

    function applyLanguage(lang) {
        currentLanguage = lang;
        if (typeof localStorage !== "undefined") {
            localStorage.setItem("preferredLanguage", lang);
        }

        if (typeof document !== "undefined") {
            document.documentElement.lang = lang;

            // Update static i18n text content
            document.querySelectorAll("[data-i18n]").forEach((element) => {
                const key = element.dataset.i18n;
                const dict = TRANSLATIONS[lang];
                if (dict && dict[key] !== undefined) {
                    if (key === "header.status_checking" && appState.healthData) {
                        renderHealthStatus(appState.healthData);
                    } else {
                        element.textContent = dict[key];
                    }
                }
            });

            // Update placeholders
            document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
                const key = element.dataset.i18nPlaceholder;
                const dict = TRANSLATIONS[lang];
                if (dict && dict[key] !== undefined) {
                    element.placeholder = dict[key];
                }
            });

            // Update active state class on language buttons
            document.querySelectorAll(".lang-btn").forEach((button) => {
                if (button.dataset.lang === lang) {
                    button.classList.add("active");
                } else {
                    button.classList.remove("active");
                }
            });

            // Rerender active dynamic panels with new translations
            if (appState.lastResult) {
                renderPrediction(appState.lastResult);
            }
            if (appState.statsData) {
                renderStats(appState.statsData);
            }
            if (appState.healthData) {
                renderHealthStatus(appState.healthData);
            }
        }
    }

    function getStatusView(status) {
        const view = STATUS_VIEWS[status] || STATUS_VIEWS.inconclusive;
        const localized = view[currentLanguage] || view.en;
        return {
            label: localized.label,
            className: view.className,
            message: localized.message
        };
    }

    function validateReview(text) {
        const trimmed = String(text || "").trim();
        if (!trimmed) {
            return ERROR_TRANSLATIONS[currentLanguage].required;
        }
        if (trimmed.length > 5000) {
            return ERROR_TRANSLATIONS[currentLanguage].too_long;
        }
        return "";
    }

    function formatPercent(value, digits) {
        return `${Number(value || 0).toFixed(digits)}%`;
    }

    function formatNumber(value) {
        const locale = currentLanguage === "vi" ? "vi-VN" : "en-US";
        return Number(value || 0).toLocaleString(locale);
    }

    function formatMetric(value, digits) {
        return Number(value || 0).toFixed(digits);
    }

    async function readJsonResponse(response) {
        const data = await response.json();
        if (!response.ok) {
            const detail = typeof data.detail === "string"
                ? data.detail
                : ERROR_TRANSLATIONS[currentLanguage].api_fallback;
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
        appState.lastResult = result;
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

        const tokenSuffix = currentLanguage === "vi" ? " từ sau tiền xử lý" : " tokens after preprocessing";
        document.getElementById("token-count-result").textContent =
            `${result.token_count}${tokenSuffix}`;
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

        const predLabelPrefix = currentLanguage === "vi" ? "Dự đoán " : "Pred ";
        const actualLabelPrefix = currentLanguage === "vi" ? "Thực tế " : "Actual ";

        for (let label = 1; label <= 5; label += 1) {
            container.appendChild(
                createElement("div", "matrix-cell matrix-label", `${predLabelPrefix}${label}`)
            );
        }

        matrix.forEach((row, rowIndex) => {
            container.appendChild(
                createElement(
                    "div",
                    "matrix-cell matrix-label",
                    `${actualLabelPrefix}${rowIndex + 1}`
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
        appState.statsData = payload;
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
        const options = { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" };
        const formattedDate = trainedDate.toLocaleString(currentLanguage === "vi" ? "vi-VN" : "en-US", options);
        if (currentLanguage === "vi") {
            document.getElementById("model-trained-at").textContent =
                `Mô hình được huấn luyện lúc ${formattedDate}`;
        } else {
            document.getElementById("model-trained-at").textContent =
                `Model trained at ${formattedDate}`;
        }

        renderDistribution(dataset);
        renderConfusionMatrix(metrics.confusion_matrix);
        renderComparison(payload.model.comparison || []);
    }

    function renderHealthStatus(data) {
        const status = document.getElementById("system-status");
        const text = document.getElementById("system-status-text");
        if (!status || !text) {
            return;
        }
        if (data && data.status === "ready") {
            status.className = "system-status ready";
            if (currentLanguage === "vi") {
                text.textContent = `Model đã sẵn sàng / sklearn ${data.scikit_learn_runtime}`;
            } else {
                text.textContent = `Model ready / sklearn ${data.scikit_learn_runtime}`;
            }
        } else {
            status.className = "system-status error";
            if (currentLanguage === "vi") {
                text.textContent = "Model không khả dụng";
            } else {
                text.textContent = "Model unavailable";
            }
        }
    }

    async function loadHealth() {
        try {
            const response = await fetch("/api/health");
            const data = await readJsonResponse(response);
            appState.healthData = data;
            renderHealthStatus(data);
        } catch (error) {
            appState.healthData = { status: "error" };
            renderHealthStatus(appState.healthData);
        }
    }

    async function loadStats() {
        try {
            const response = await fetch("/api/stats");
            const data = await readJsonResponse(response);
            renderStats(data);
        } catch (error) {
            document.getElementById("model-trained-at").textContent =
                ERROR_TRANSLATIONS[currentLanguage].stats_failed;
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
        submitButton.textContent = currentLanguage === "vi" ? "Đang phân tích..." : "Analyzing...";

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
            errorBox.textContent = translateError(error.message, currentLanguage);
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = TRANSLATIONS[currentLanguage]["form.submit"];
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
        button.textContent = currentLanguage === "vi" ? "Đang tải..." : "Loading...";

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
            errorBox.textContent = `${ERROR_TRANSLATIONS[currentLanguage].example_failed}${translateError(error.message, currentLanguage)}`;
        } finally {
            button.disabled = false;
            const btnKey = `analysis.${type === "contradictory" ? "contradictory" : type}`;
            button.textContent = TRANSLATIONS[currentLanguage][btnKey] || originalText;
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
        document.querySelectorAll(".lang-btn").forEach((button) => {
            button.addEventListener("click", () => {
                applyLanguage(button.dataset.lang);
            });
        });

        // Initialize UI translation from stored preferences
        applyLanguage(currentLanguage);

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
