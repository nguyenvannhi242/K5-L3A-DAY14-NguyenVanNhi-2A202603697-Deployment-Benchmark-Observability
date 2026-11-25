# Deployment Information — Day 14

## Public URL

[https://day14-production-agent-0m8h.onrender.com](https://day14-production-agent-0m8h.onrender.com)

## Platform

Render Free, vùng Ohio (US East), môi trường `Production`. Web service `day14-production-agent` và Key Value `day14-agent-redis` được tạo qua dashboard. Web service build bằng Docker từ nhánh `main`, với root directory và build context là `06-lab-complete/`. Render kiểm tra `/health` để xác nhận deploy. URL gốc chuyển hướng đến Swagger UI tại `/docs`. [Cấu hình Blueprint tương ứng](06-lab-complete/render.yaml)

Ngày 25/11/2026, Render ghi nhận instance nhiều lần vượt giới hạn RAM 512 MB, làm URL public trả HTTP 502. Dockerfile dùng một worker Uvicorn mặc định để giảm mức sử dụng RAM trên Render Free.

## Test Commands

Nhập API key của web service từ Render khi được nhắc. Các lệnh chỉ in mã HTTP.

```bash
BASE='https://day14-production-agent-0m8h.onrender.com'
read -rsp 'Agent API key: ' AGENT_API_KEY
printf '\n'
curl -sS --max-time 90 -o /dev/null -w 'GET /health: %{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w 'GET /ready: %{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w 'POST /ask (without key): %{http_code}\n' \
  -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
printf 'header = "X-API-Key: %s"\n' "$AGENT_API_KEY" |
  curl --config - -sS -o /dev/null -w 'POST /ask (with key): %{http_code}\n' \
    -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
unset AGENT_API_KEY
```

Kết quả thực tế từ Ubuntu WSL2 ngày 25/11/2026.

| Phép kiểm | HTTP |
| --- | ---: |
| `GET /health` | `200` |
| `GET /ready` | `200` |
| `POST /ask` thiếu API key | `401` |
| `POST /ask` với API key hợp lệ | `200` |

Phép kiểm URL public của checker gốc cũng báo đạt khi gọi `GET /health`.

## Environment Variables

| Biến | Nguồn giá trị khi deploy |
| --- | --- |
| `PORT` | Render cấp cổng `10000`, Dockerfile đọc khi khởi động |
| `AGENT_WORKERS` | Dockerfile mặc định dùng `1` worker |
| `ENVIRONMENT` | `production`, đặt trong dashboard |
| `REDIS_URL` | URL nội bộ của Render Key Value, đặt trong dashboard |
| `AGENT_API_KEY` | Giá trị sinh bằng nút Generate trong dashboard |

## Screenshots

- [Dashboard với web service và Key Value](screenshots/dashboard.png)
- [Agent đang chạy trên Render](screenshots/running.png)
- [Bốn phản hồi HTTP từ lượt kiểm tra public](screenshots/test.png)
