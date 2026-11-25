# Benchmark & Observability Report — Day 14

**Họ tên:** Nguyen Van Nhi

**Ngày chạy CP7:** 25/11/2026

**Môi trường:** Ubuntu WSL2 x86_64, Python 3.12.3, 12 CPU logic nhìn thấy trong WSL và khoảng 7,68 GiB RAM. Client và agent chạy localhost trên cùng máy. Mỗi lượt chạy dùng một tiến trình agent.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
| --- | --- | --- |
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của lab để đánh giá trải nghiệm của phần lớn request, kể cả nhóm chậm hơn mức trung vị. |
| Error rate `/ask` | ≤ 2% | Tính trên mọi request đo được, gồm phản hồi ngoài `200` và lỗi kết nối. |
| Accuracy trên golden dataset | ≥ 85% | Ngưỡng quality gate cơ bản của Exercise 7.3. Lượt nghiệm thu v2 sau sửa yêu cầu 100% và không regression. |

### Exercise 7.1 — Metrics

Sau 23 câu eval v2 và một request thử riêng, `GET /metrics` ghi nhận:

```text
http_requests_total{method="POST",route="/ask",status="200"} 24.0
agent_in_flight_requests 0.0
# TYPE agent_question_length_chars histogram
agent_question_length_chars_count 24.0
agent_question_length_chars_sum 1106.0
```

- **Counter** `http_requests_total` đếm số request tích lũy theo method, route và status.
- **Gauge** `agent_in_flight_requests` tăng khi nhận request và giảm khi xử lý xong.
- **Histogram** `agent_question_length_chars` ghi phân bố độ dài câu hỏi qua các bucket. Metric mới đo số ký tự ngay khi endpoint nhận payload hợp lệ.
- Dùng route template và nhãn `unmatched` giúp số time series hữu hạn. Dùng URL nguyên văn có thể tạo một time series mới cho mỗi đường dẫn lạ và làm Prometheus tốn RAM.

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

Các lượt đo dùng v2 trước khi sửa knowledge base, model `mock-llm-small`, với 300 request tính điểm mỗi lượt. Script gửi một request warm-up riêng và tính percentile trên các phản hồi `200`. Tỷ lệ lỗi mô phỏng được giữ ở `MOCK_ERROR_RATE=0.01`.

### 2.1 Concurrency vs latency (agent v2)

Giữ `MOCK_SLOW_RATE=0.03` cho cả bốn lượt.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO | File |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 3.96 | 195.3 | 224.3 | 1702.9 | 0.67% | PASS | [JSON](reports/load_v2_c1.json) |
| 10 | 34.13 | 187.2 | 228.1 | 1699.0 | 1.00% | PASS | [JSON](reports/load_v2_c10.json) |
| 50 | 103.79 | 198.1 | 261.2 | 1715.6 | 0.33% | PASS | [JSON](reports/load_v2_c50.json) |
| 100 | 76.46 | 501.1 | 3140.2 | 3526.2 | 1.33% | FAIL | [JSON](reports/load_v2_c100.json) |

RPS đạt cao nhất ở concurrency 50 trong loạt đo. Khi tăng lên 100, RPS giảm từ **103.79** xuống **76.46**, còn p95 tăng từ **261.2** lên **3140.2 ms**. Kết quả cho thấy tăng số request đồng thời không làm thông lượng tăng tuyến tính. Client và server chạy cùng máy, dùng chung tài nguyên, và bài đo chưa tách chi phí lập lịch, kết nối hay xử lý trong agent. Concurrency 100 vi phạm SLO p95, còn error rate của cả bốn lượt nằm trong ngưỡng.

### 2.2 Tail latency

Khởi động lại agent cho mỗi giá trị `MOCK_SLOW_RATE`. Giữ concurrency 20 và các cấu hình mô phỏng còn lại cố định.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) | File |
| --- | ---: | ---: | ---: | --- |
| 0 | 188.9 | 216.1 | 221.4 | [JSON](reports/load_v2_slow_0.json) |
| 0.03 | 221.7 | 219.7 | 1696.3 | [JSON](reports/load_v2_slow_0.03.json) |
| 0.1 | 363.2 | 1699.5 | 1725.1 | [JSON](reports/load_v2_slow_0.1.json) |

Ở slow rate 0.03, p99 tăng từ **221.4** lên **1696.3 ms**, trong khi avg chỉ tăng từ **188.9** lên **221.7 ms**. Vì vậy p99 nhạy hơn với nhóm request chậm hiếm gặp. Khi slow rate lên 0.1, p95 cũng lên **1699.5 ms** và vi phạm SLO dù avg vẫn dưới 500 ms.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

Eval cả ba phiên bản với `MOCK_ERROR_RATE=0` để đo chất lượng câu trả lời. `MOCK_SLOW_RATE` giữ ở 0.03. V2 gốc so với baseline v1, v2 sau sửa so với baseline v2 gốc.

| Chỉ số | [Agent v1](reports/eval_v1.json) | [Agent v2](reports/eval_v2.json) | [Agent v2 sau khi sửa KB](reports/eval_v2_fixed.json) |
| --- | ---: | ---: | ---: |
| Accuracy | 4.35% (1/23) | 91.30% (21/23) | 100.00% (23/23) |
| Avg tokens / câu | 57.5 | 109.3 | 117.2 |
| Tổng cost (USD) | 0.000409 | 0.000764 | 0.000821 |
| Cost / câu đúng (USD) | 0.00040935 | 0.00003639 | 0.00003570 |
| Latency p50 (ms) | 161.8 | 195.6 | 198.1 |
| Latency p95 (ms) | 1513.1 | 230.3 | 220.7 |
| Lỗi HTTP hoặc kết nối | 0 | 0 | 0 |
| Quality gate | FAIL · ngưỡng 85% | PASS · ngưỡng 85% | PASS · ngưỡng 100% |

**Các câu v2 chưa đạt trước khi sửa**

| ID | Keyword bị thiếu | Cách sửa |
| --- | --- | --- |
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm tài liệu về JWT, mô tả claim, chữ ký, hạn dùng và cách bản mẫu đối chiếu API key. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm tài liệu về HPA, gồm CPU, memory, custom metrics và cách so giá trị hiện tại với mục tiêu. |

Đã chạy lại với `--min-accuracy 1.0 --baseline reports/eval_v2.json` (đường dẫn tính từ gốc repo). Cả hai câu trên chuyển sang PASS và cả 21 câu đã đạt tiếp tục PASS. [Knowledge base](06-lab-complete/benchmark-observability/develop/utils/mock_llm.py)

V2 dùng thêm token vì đưa tài liệu truy xuất vào prompt. Tổng chi phí tăng, còn chi phí cho mỗi câu đúng giảm do số câu đúng tăng từ 1 lên 21 rồi 23. p50 tăng từ 161.8 ms ở v1 lên 195.6 ms ở v2 gốc. p95 của eval chỉ phản ánh 23 câu mỗi lượt và chịu ảnh hưởng của request chậm ngẫu nhiên, nên chưa đủ để kết luận v2 có tail latency thấp hơn v1.

**Quality gate trong CI.** Khi kiểm tra một PR, khởi động agent từ code ứng viên với lỗi mô phỏng tắt, lấy file baseline từ nhánh đích rồi chạy `run_eval.py` với `--baseline` và `--min-accuracy`. Script trả exit code `1` nếu accuracy dưới ngưỡng hoặc có câu đang PASS trong baseline chuyển sang FAIL. Nếu đặt job eval thành required check, kết quả đó sẽ chặn merge. Thư mục `reports/` giữ riêng JSON baseline và JSON của lượt nghiệm thu.

---

## 4. Observability stack (production)

> Phần 4–6 sẽ được hoàn thiện với số liệu và ảnh ở CP8.

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [ ] Một trace lỗi trong Jaeger (có event `exception`)
- [ ] Trang Alerts của Prometheus với ít nhất 2 alert đang **firing** cùng lúc

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

...

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

...

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. ...
  2. ...
  3. ...
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

...
