# Phân tích độ nhất quán review

Dự án dự đoán rating từ 1 đến 5 dựa trên nội dung review nhà hàng bằng
tiếng Anh, sau đó so sánh rating dự đoán với rating người dùng đã chọn.

Đây là bài toán phân tích độ nhất quán nội dung và rating. Dataset không có
nhãn giả mạo hoặc spam, vì vậy kết quả không được dùng để kết luận một review
là giả.

## Pipeline

```text
CSV gốc
  -> kiểm tra rating và review
  -> chuẩn hóa contraction và giữ từ phủ định
  -> làm tròn rating nửa sao theo half-up
  -> loại review rỗng và cặp text_clean + rating bị trùng
  -> StratifiedGroupKFold theo text_clean
  -> TF-IDF word + character
  -> Logistic Regression với trọng số lớp được chọn bằng cross-validation
  -> artifact joblib + model metadata
  -> FastAPI + giao diện HTML/CSS/JavaScript
```

## Cấu trúc chính

```text
Review_consistency/
|-- data/raw/restaurant_reviews.csv
|-- models/
|   |-- review_rating_pipeline.joblib
|   |-- model_metadata.json
|-- notebooks/sentiment_and_spam_analysis.ipynb
|-- src/
|   |-- preprocessing.py
|   |-- modeling.py
|   |-- train.py
    |-- config.py
|   `-- predict.py
|-- static/
|   |-- css/style.css
|   |-- js/main.js
|   |-- favicon.svg
|   `-- index.html
|-- tests/
|-- main.py
|-- requirements.txt
`-- requirements-dev.txt
```

## Dữ liệu

Dataset gốc có 10.000 dòng. Pipeline hiện giữ 9.311 dòng sau khi:

- Loại rating thiếu, không phải số và review thiếu.
- Làm tròn 144 rating nửa sao theo half-up.
- Loại 16 review trở thành rỗng sau tiền xử lý.
- Loại 627 cặp `text_clean + Rating` bị trùng.
- Giữ review cùng nội dung nhưng rating khác nhau trong cùng một group.

Phân phối sau làm sạch:

| Rating | Số mẫu | Tỷ lệ |
|---|---:|---:|
| 1 | 1.705 | 18,31% |
| 2 | 684 | 7,35% |
| 3 | 1.186 | 12,74% |
| 4 | 2.349 | 25,23% |
| 5 | 3.387 | 36,38% |

Accuracy không phải metric chính vì lớp 5 sao chiếm tỷ trọng lớn. Quá trình
chọn model ưu tiên macro-F1, sau đó là MAE và weighted-F1.

## Model production

Model hiện tại dùng:

- Word TF-IDF unigram và bigram, tối đa 12.000 đặc trưng.
- Character TF-IDF `char_wb` từ 3 đến 5 ký tự, tối đa 20.000 đặc trưng.
- Logistic Regression với `C=0.25`.
- Trọng số lớp được tính từ tần suất của từng fold.
- Group split để cùng một `text_clean` không xuất hiện ở cả train và test.

Kết quả holdout:

| Metric | Giá trị |
|---|---:|
| Accuracy | 0,6289 |
| Macro-F1 | 0,5737 |
| Weighted-F1 | 0,6349 |
| MAE | 0,4592 |
| Trong sai số một sao | 0,9366 |
| Recall lớp 2 sao | 0,4526 |

Các con số chính xác, cấu hình, confusion matrix, dataset hash và phiên bản
thư viện nằm trong `models/model_metadata.json`.

## Cài đặt

Yêu cầu Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

## Huấn luyện

```powershell
python -m src.train
```

Script thực hiện group holdout, inner cross-validation, so sánh baseline,
kiểm tra ngưỡng chất lượng và ghi:

- `models/review_rating_pipeline.joblib`
- `models/model_metadata.json`

Các file `.pkl` cũ không còn được runtime sử dụng.

## Chạy ứng dụng

```powershell
python main.py
```

Hoặc:

```powershell
uvicorn main:app --reload
```

Mở `http://127.0.0.1:8000`.

## API

### `POST /api/predict`

Request:

```json
{
  "review_text": "The food was excellent and the service was friendly.",
  "actual_rating": 5
}
```

Response chính:

- `actual_rating`, `predicted_rating`, `rating_gap`
- `class_scores`, `top_model_score`
- `cleaned_text`, `token_count`
- `status`, `needs_review`

Ba trạng thái:

- `consistent`: đủ thông tin và lệch tối đa một sao.
- `potential_mismatch`: đủ thông tin và lệch từ hai sao.
- `inconclusive`: dưới hai token hoặc model score thấp hơn ngưỡng.

Endpoint khác:

- `GET /api/stats`
- `GET /api/model-info`
- `GET /api/health`
- `GET /docs`

## Kiểm thử

```powershell
pytest
node --test tests\js\main.test.js
```

Test bao phủ preprocessing, group split, artifact, ngưỡng chất lượng,
validation API, ba trạng thái kết quả và logic giao diện.

## Giới hạn

- Model chỉ hỗ trợ review tiếng Anh.
- Model score chưa được hiệu chỉnh thành xác suất.
- Review ngắn hoặc mơ hồ có thể không đủ thông tin để kết luận.
- Dự án không dùng reviewer metadata, thời gian, hình ảnh hoặc hành vi đăng.
- Muốn phát hiện giả mạo cần dataset có nhãn và quy trình đánh giá riêng.
