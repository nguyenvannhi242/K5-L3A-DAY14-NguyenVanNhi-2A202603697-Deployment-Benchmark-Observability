# Day 14 Lab — Mission Answers

## Part 1 — Localhost vs Production

### Exercise 1.1 — Anti-patterns trong bản develop

1. **Để thông tin nhạy cảm trong mã nguồn.** [develop/app.py dòng 17–18](01-localhost-vs-production/develop/app.py#L17-L18) chứa API key giả và chuỗi kết nối có thông tin đăng nhập minh họa. Nếu dùng giá trị thật, người có quyền đọc repo hoặc lịch sử Git có thể lấy được chúng. [production/config.py dòng 27–32](01-localhost-vs-production/production/config.py#L27-L32) đọc API key từ biến môi trường.
2. **Ghi câu hỏi, câu trả lời và API key bằng `print()`.** [develop/app.py dòng 32–38](01-localhost-vs-production/develop/app.py#L32-L38) đưa cả dữ liệu người dùng và key vào log. [production/app.py dòng 110–122](01-localhost-vs-production/production/app.py#L110-L122) ghi các trường như tên sự kiện và độ dài thay cho nội dung và key.
3. **Cố định cấu hình.** [develop/app.py dòng 21–22](01-localhost-vs-production/develop/app.py#L21-L22) đặt sẵn `DEBUG` và `MAX_TOKENS`. [production/config.py dòng 17–29](01-localhost-vs-production/production/config.py#L17-L29) cho phép thay cấu hình qua môi trường mà không phải sửa mã.
4. **Chỉ bind localhost và cố định cổng 8000.** [develop/app.py dòng 49–53](01-localhost-vs-production/develop/app.py#L49-L53) khiến agent khó dùng với container và nền tảng cấp cổng qua `PORT`. [production/app.py dòng 194–198](01-localhost-vs-production/production/app.py#L194-L198) lấy địa chỉ và cổng từ cấu hình.
5. **Luôn bật auto-reload.** [develop/app.py dòng 53](01-localhost-vs-production/develop/app.py#L53) để `reload=True`, nên thay đổi file có thể làm tiến trình phục vụ restart. [production/app.py dòng 194–198](01-localhost-vs-production/production/app.py#L194-L198) chỉ bật reload khi `DEBUG=true`, mặc định là `false`.
6. **Thiếu liveness và readiness.** [develop/app.py dòng 25–43](01-localhost-vs-production/develop/app.py#L25-L43) chỉ có route gốc và route hỏi agent. [production/app.py dòng 135–161](01-localhost-vs-production/production/app.py#L135-L161) cung cấp `/health` và `/ready` để nền tảng kiểm tra tiến trình và quyết định lúc nào nên định tuyến request.
7. **Thiếu hook dọn tài nguyên của ứng dụng.** Bản develop dùng vòng đời mặc định của Uvicorn. [production/app.py dòng 39–74](01-localhost-vs-production/production/app.py#L39-L74) thêm FastAPI lifespan để chuyển trạng thái sẵn sàng và thực hiện bước dọn dẹp khi tắt.

### Exercise 1.2 — Chạy bản develop

Chạy `python app.py` trong `01-localhost-vs-production/develop/` bằng Ubuntu WSL2, Python 3.12.3. Cài dependency theo hai file `requirements.txt` của Part 1 trong môi trường ảo tạm.

```bash
curl -sS -w '\nHTTP %{http_code}\n' -X POST 'http://localhost:8000/ask?question=Hello'
```

```text
{"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
HTTP 200
```

`GET /health` trả HTTP `404` với body `{"detail":"Not Found"}`. Bản develop nhận `question` qua query và đã được dừng trước khi chạy bản production trên cùng cổng.

### Exercise 1.3 — So sánh develop và production

| Hạng mục | Develop | Production | Vì sao quan trọng |
| --- | --- | --- | --- |
| Cấu hình và secret | Hằng số trong mã, có giá trị minh họa cho key và thông tin đăng nhập | Đọc cấu hình từ biến môi trường. `Settings.validate()` yêu cầu `AGENT_API_KEY` khi `ENVIRONMENT=production` | Cùng một bản build chạy được ở nhiều môi trường. Có thể thay key mà không phải sửa mã hoặc build lại. |
| Địa chỉ, cổng và reload | `localhost:8000`, luôn bật reload | `HOST`, `PORT`, `DEBUG` lấy từ môi trường. Mặc định bind `0.0.0.0` và tắt reload | Container nhận được kết nối qua cổng cấp cho ứng dụng, và tiến trình tránh restart do thay đổi file khi chạy production. |
| Liveness và readiness | Thiếu cả hai route. `GET /health` trả `404` trong lần chạy thử | `/health` báo tiến trình còn sống. `/ready` dựa trên cờ vòng đời của ứng dụng và có nhánh trả `503` | Nền tảng có thể quyết định restart khi tiến trình gặp sự cố hoặc tạm ngừng chuyển traffic khi ứng dụng chưa sẵn sàng. |
| Logging | `print()` kèm câu hỏi, câu trả lời và giá trị key minh họa | Dùng `logging` và khai báo định dạng JSON. Sự kiện request/response ghi metadata, ví dụ độ dài | Trường log giúp tìm và tổng hợp sự kiện. Chỉ ghi metadata cần thiết giúp giảm nguy cơ lộ dữ liệu. |
| Shutdown | Dùng shutdown mặc định của Uvicorn | Thêm FastAPI lifespan để cập nhật cờ readiness và chạy đoạn dọn dẹp của ứng dụng | Khi nền tảng dừng tiến trình, ứng dụng có điểm để đóng kết nối và giải phóng tài nguyên. |
| Đầu vào `/ask` | Query `?question=Hello` | JSON body chứa `question`. Thiếu câu hỏi trả `422` | Client biết đặt dữ liệu ở đâu và nhận được thông báo rõ khi thiếu trường bắt buộc. |

#### Kiểm tra bản production

Khởi động bằng `HOST=127.0.0.1 PORT=8000 DEBUG=false ENVIRONMENT=development LLM_MODEL=gpt-4o-mini python app.py` từ `01-localhost-vs-production/production/`, với mock LLM.

```bash
curl -sS -w '\nHTTP %{http_code}\n' -X POST 'http://localhost:8000/ask' \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -w '\nHTTP %{http_code}\n' 'http://localhost:8000/health'
curl -sS -w '\nHTTP %{http_code}\n' 'http://localhost:8000/ready'
```

```text
{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","model":"gpt-4o-mini"}
HTTP 200
{"status":"ok","uptime_seconds":0.4,"version":"1.0.0","environment":"development","timestamp":"2026-11-25T10:12:45.845928+00:00"}
HTTP 200
{"ready":true}
HTTP 200
```

Sau khi gửi SIGTERM, Uvicorn ghi `Application shutdown complete.` và shell nhận exit code `0`. Lúc gửi tín hiệu, các request kiểm tra đã hoàn tất.

Bản production khai báo format JSON, nhưng khi thiếu `OPENAI_API_KEY`, `config.py` gọi `logging.warning()` trước `logging.basicConfig()` của app. Lần chạy với mock không thấy các dòng log INFO của ứng dụng trong phần kiểm tra, nên kết quả chỉ xác nhận shutdown qua log Uvicorn.

## AI log

- **CP0.** Dùng Codex để đối chiếu kế hoạch với tài liệu K5 và kiểm tra môi trường. Codex xác nhận Python trong Ubuntu là `3.12.3`, `os.name=posix`, container `hello-world` chạy được và GitHub báo repo Public. Tôi đã xác nhận CP0 trước khi chuyển sang CP1.
- **CP1.** Dùng Codex để chạy hai ví dụ, đối chiếu code và soạn câu trả lời Exercise 1.1–1.3. Các kết quả HTTP trong mục CP1 lấy từ lệnh chạy trong Ubuntu WSL2. Phần ghi chép đang chờ tôi đối chiếu trước khi sang CP2.
