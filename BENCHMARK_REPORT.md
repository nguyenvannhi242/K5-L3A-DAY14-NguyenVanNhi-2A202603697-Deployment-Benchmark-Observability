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

Đo ngày 25/11/2026 trong Ubuntu WSL2 với Docker Engine 28.5.1 và project `k5-day14-observability`. Image agent cần khai báo `PYTHONUSERBASE=/home/agent/.local` để Python của user non-root tìm thấy dependency đã chép từ builder. `promtool check rules` tìm thấy **4 rule hợp lệ**, và `promtool test rules /p/alert_rules_test.yml` trả `SUCCESS`. [Dockerfile](06-lab-complete/benchmark-observability/production/Dockerfile)

### 4.1 Dashboard và Exercise 7.4

[Ảnh Grafana khi Locust chạy trên 3 replica](screenshots/grafana-dashboard.png) hiển thị traffic, error rate, latency p95 và saturation in-flight. Tại mẫu Prometheus lúc **21:14:25 GMT+7** trong lượt 3 replica, traffic là **67.20 req/s**, error rate **0.97%** và có **13 request in-flight**.

1. **Latency.** p95 `/ask` là **292.87 ms**, avg **230.82 ms**. Khoảng cách **62.05 ms** cho thấy nhóm request chậm hơn trải nghiệm trung bình. p95 này là ước lượng từ bucket Prometheus ở cửa sổ một phút. CSV Locust tính percentile trên cả lượt đo.
2. **Cân bằng tải.** Ba replica nhận lần lượt `172.21.0.4:8000` 22.61, `172.21.0.8:8000` 22.21, `172.21.0.9:8000` 22.39 req/s. Chênh lệch nhỏ cho thấy Nginx phân phối khá đều trong mẫu đã chọn.
3. **Token.** Input đạt **4899.23 token/s**, output **2600.96 token/s**. Input của v2 tính cả system prompt, câu hỏi và đoạn tài liệu truy xuất. Output chỉ tính câu trả lời.
4. **Phạm vi scrape.** `GET http://localhost:8080/metrics` trả **HTTP 404**. Nginx chặn route đó ở cổng vào, còn Prometheus scrape trực tiếp các agent trên mạng nội bộ.

### 4.2 Thí nghiệm cảnh báo

Giữ Locust 30 user, ramp 5 user/s. Bắt đầu tính thời gian ngay trước lệnh Compose áp dụng cấu hình cho agent, sau đó thăm dò API Alerts mỗi hai giây. Ở thí nghiệm B, giữ nguyên cấu hình A để kiểm tra hai alert cùng `firing`.

| Thí nghiệm | Thay đổi | Alert quan sát | Thời gian từ lúc đổi | Panel phản ánh |
| --- | --- | --- | ---: | --- |
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` firing ở mức 22.49% lỗi | 98.0 s | Error rate |
| B | `MOCK_SLOW_RATE=0.3`, giữ A | `AgentHighLatencyP95` firing ở p95 1891.78 ms cùng `AgentHighErrorRate` ở 21.18% lỗi | 153.2 s | Latency p95 |

[Ảnh trang Alerts khi hai alert cùng firing](screenshots/prometheus-alert-firing.png). Rule error rate yêu cầu vượt 5% liên tục một phút. Rule p95 yêu cầu vượt một giây liên tục hai phút. Thời gian quan sát được gồm cả lúc thay container, scrape và chu kỳ đánh giá trước khi trạng thái thay đổi. `LLMCostBurnRateHigh` trong ảnh đã firing trước A và B, khi model nhỏ đang chịu tải.

Nếu chuyển `AGENT_VERSION=v1` như thí nghiệm E, các rule hiện tại vẫn chỉ đo lỗi HTTP, latency, scrape và chi phí. Để phát hiện chất lượng giảm, chạy eval trên golden dataset với baseline, theo dõi tỷ lệ đạt theo phiên bản và đặt quality gate trước khi triển khai.

### 4.3 Debug bằng trace

**Trace chậm.** ID `abc89ef74b99f3dc56a8384ebc589fb0`, tổng **1723.986 ms**. Span con tốn nhiều thời gian nhất là `chat mock-llm-small` với **1700.077 ms** (**98.61%** tổng thời gian). Phần lớn độ trễ nằm trong bước gọi mock LLM. [Ảnh trace chậm](screenshots/jaeger-slow-trace.png)

```json
{"ts":"2026-11-25T14:07:29.561637+00:00","level":"INFO","service":"observable-agent","instance":"8812fe951128","event":"llm_call","trace_id":"abc89ef74b99f3dc56a8384ebc589fb0","span_id":"7fa3b839c2a78825","request_id":"e3c9ac6059d8","model":"mock-llm-small","agent_version":"v2","input_tokens":95,"output_tokens":55,"cost_usd":0.000047,"llm_ms":1698.6}
```

**Trace lỗi.** ID `7218f9a58d4a0a61dc11a95a3c9f9c10`, tổng **101.385 ms**, root request trả `503`. Span `chat mock-llm-small` có event `exception` với `utils.mock_llm.LLMError` và thông báo `Upstream LLM error: 503 Service Unavailable (mock)`. [Ảnh trace lỗi](screenshots/jaeger-error-trace.png)

```json
{"ts":"2026-11-25T14:10:36.215760+00:00","level":"INFO","service":"observable-agent","instance":"8812fe951128","event":"llm_error","trace_id":"7218f9a58d4a0a61dc11a95a3c9f9c10","span_id":"83794de63ca9f505","request_id":"dca793bc1e86","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Cùng model `mock-llm-small`, v2, `MOCK_ERROR_RATE=0.01`, `MOCK_SLOW_RATE=0.03`, 100 user và ramp 10 user/s cho hai lượt. Dùng `docker compose run --rm --no-deps locust` để Locust không đưa dependency agent về số replica mặc định. Chỉ bắt đầu sau khi Compose và Prometheus báo đủ số replica. Xác minh lại số replica sau khi Locust dừng. Các số dưới đây lấy từ dòng `POST /ask` trong CSV. RPS và error rate làm tròn hai chữ số thập phân.

| Số replica | Request | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures | Error rate | File |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 7172 | 65.08 | 190 | 250 | 1700 | 79 | 1.10% | [CSV](benchmark-results/scale_1_stats.csv) |
| 3 | 7142 | 64.80 | 190 | 220 | 1700 | 74 | 1.04% | [CSV](benchmark-results/scale_3_stats.csv) |

Tăng từ một replica lên ba giảm p95 **30 ms**, trong khi p50 và p99 giữ nguyên. RPS gần như giữ nguyên ở cùng số user, và Locust nghỉ giữa mỗi lượt hỏi. Kết quả này chưa đo thông lượng tối đa. Trace chậm cho thấy chính mock LLM chiếm phần lớn thời gian của request chậm, nên thêm replica vẫn để lại p99 **1700 ms** trong phép đo này.

Stack được dọn bằng `docker compose -p k5-day14-observability down -v` sau khi thu đủ ảnh và CSV.

---

## 6. Kết luận

1. Kiểm tra số target và replica trước khi đo. Một lệnh khởi động workload có thể đổi topology thông qua dependency của Compose.
2. Đọc p95 cùng p99. Điểm giữa phân bố và p95 có thể cải thiện dù nhóm request chậm nhất giữ nguyên độ trễ.
3. Dùng `trace_id` để nối log với trace và xem bước nào chiếm thời gian hoặc phát sinh exception.

Nếu đưa agent lên production, nên thu tỷ lệ lỗi và timeout ở Nginx để thấy lỗi trước khi request tới agent, đồng thời theo dõi tỷ lệ đạt eval theo phiên bản để phát hiện suy giảm chất lượng.
