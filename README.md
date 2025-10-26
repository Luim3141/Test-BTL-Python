# Premier League Data Engineering & Analytics Toolkit

This project demonstrates how to crawl player statistics for the 2024-2025 Premier League season, enrich the dataset with transfer values, expose the information through REST APIs, and run analytical workflows (aggregations, clustering, PCA visualisation).

## Project Structure

```
.
├── app.py                    # Flask REST API
├── analytics.py              # Statistics, clustering and PCA routines
├── btl/                      # Reusable modules (database + scrapers)
├── data/                     # SQLite database location
├── artifacts/                # Generated CSV files and plots
├── lookup.py                 # CLI client that queries the Flask API
├── requirements.txt          # Python dependencies
└── scripts/
    └── collect_data.py       # Crawl FBref + FootballTransfers and populate SQLite
```

## 1. Chuẩn bị môi trường

Thực hiện bước này trước khi chạy bất kỳ thành phần nào của bài tập.

1. Tạo và kích hoạt môi trường ảo (tuỳ chọn nhưng được khuyến nghị).

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Cài đặt toàn bộ phụ thuộc Python.

   ```bash
   pip install -r requirements.txt
   ```

## 2. Thu thập dữ liệu (I.1 & I.2)

Thực thi script thu thập dữ liệu đúng thứ tự yêu cầu: trước tiên lấy thống kê cầu thủ từ FBref, sau đó bổ sung giá trị chuyển nhượng từ FootballTransfers và lưu toàn bộ vào SQLite.

```bash
python scripts/collect_data.py --season 2024-2025 --min-minutes 90
```

Script này sẽ:

* Tải bảng `Standard Stats` của từng đội bóng tại FBref, lọc cầu thủ có thời lượng thi đấu > 90 phút và ghi vào bảng `player_stats` của `data/premier_league.db`.
* Với mỗi cầu thủ vừa ghi nhận, cố gắng lấy giá trị chuyển nhượng từ [footballtransfers.com](https://www.footballtransfers.com) và lưu vào bảng `player_transfers`.
* Đối với chỉ số không tồn tại, dữ liệu sẽ được đặt thành `N/a`.

### Gợi ý xử lý CAPTCHA hoặc rate-limit

* Client HTTP tích hợp độ trễ ngẫu nhiên giữa các request, retry với exponential backoff khi gặp HTTP 429/5xx và mô phỏng `User-Agent` của trình duyệt desktop.
* Có thể bổ sung lưu cache HTML, xoay proxy/VPN, hoặc chuyển sang Selenium (undetected-chromedriver) nếu gặp CAPTCHA phức tạp.

## 3. Cung cấp RESTful API tra cứu dữ liệu (II.1)

Sau khi cơ sở dữ liệu được tạo ở bước 2, khởi chạy dịch vụ Flask để cung cấp API theo yêu cầu đề bài:

```bash
python app.py
```

Các endpoint chính:

* `GET /api/players?name=<tên cầu thủ>`: trả về toàn bộ chỉ số của cầu thủ tương ứng.
* `GET /api/players?club=<tên câu lạc bộ>`: trả về toàn bộ cầu thủ thuộc câu lạc bộ đó.

## 4. Viết chương trình tra cứu bằng Requests (II.2)

Khi Flask API đang chạy, sử dụng CLI `lookup.py` để truy vấn và xuất dữ liệu thành bảng + CSV:

```bash
python lookup.py --name "Erling Haaland"
python lookup.py --club "Liverpool"
```

File CSV kết quả sẽ được đặt tên theo cầu thủ hoặc câu lạc bộ (ví dụ: `Erling Haaland.csv`).

## 5. Phân tích thống kê và máy học (III)

`analytics.py` đọc dữ liệu trong SQLite và thực hiện các bước theo đề bài:

1. Tính trung vị, trung bình, độ lệch chuẩn cho từng chỉ số của mỗi đội và lưu vào `artifacts/team_statistics.csv`.
2. Tìm đội bóng dẫn đầu từng chỉ số, ghi vào `artifacts/best_team_by_metric.csv`, đồng thời hỗ trợ đánh giá phong độ.
3. Đề xuất phương pháp định giá cầu thủ dựa trên dữ liệu, kết quả lưu tại `artifacts/player_valuation_scores.csv`.
4. Chạy K-Means, vẽ biểu đồ Elbow và Silhouette, lưu cụm vào `artifacts/player_clusters.csv`.
5. Giảm số chiều bằng PCA (2D, 3D) và vẽ scatter plot vào thư mục `artifacts/`.

Chạy toàn bộ pipeline bằng:

```bash
python analytics.py
```

## 6. Tổng hợp báo cáo cuối cùng

Sử dụng dữ liệu và biểu đồ trong thư mục `artifacts/` cùng với nhận xét, phân tích bổ sung để hoàn thiện báo cáo PDF theo yêu cầu nộp bài.
