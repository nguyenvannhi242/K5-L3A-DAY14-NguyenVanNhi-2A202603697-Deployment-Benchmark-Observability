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

## Part 2 — Docker Containerization

### Exercise 2.1 — Dockerfile cơ bản

1. **Base image.** Bản develop dùng `python:3.11`, bản phân phối Python đầy đủ. [develop/Dockerfile dòng 8](02-docker/develop/Dockerfile#L8)
2. **Working directory.** `WORKDIR /app` đặt thư mục làm việc bên trong container cho các lệnh tiếp theo. [develop/Dockerfile dòng 11](02-docker/develop/Dockerfile#L11)
3. **Thứ tự copy.** Docker copy `requirements.txt` rồi chạy `pip install` trước khi copy code. Nếu chỉ sửa code, Docker có thể dùng lại layer cài dependency. [develop/Dockerfile dòng 13–24](02-docker/develop/Dockerfile#L13-L24)
4. **CMD và ENTRYPOINT.** `CMD` cung cấp lệnh mặc định hoặc đối số mặc định cho `ENTRYPOINT`. Đối số sau tên image trong `docker run` thay thế `CMD`. `ENTRYPOINT` xác định chương trình chính và có thể được thay bằng `--entrypoint`. Image develop đặt `CMD ["python", "app.py"]`. [develop/Dockerfile dòng 29–30](02-docker/develop/Dockerfile#L29-L30)

### Exercise 2.2 — Build và chạy container develop

Build từ gốc repo bằng `docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .`. Sau khi chạy image với `-p 127.0.0.1:8000:8000`, `GET /health` trả HTTP `200` với `{"status":"ok","uptime_seconds":0.2,"container":true}`.

```bash
curl -sS -w '\nHTTP %{http_code}\n' -X POST \
  'http://localhost:8000/ask?question=What%20is%20Docker%3F'
```

```text
{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
HTTP 200
```

### Exercise 2.3 — Multi-stage build và dung lượng

Chạy `docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .` từ gốc repo. Stage `builder` dùng `python:3.11-slim`, cài công cụ build và cài dependency vào `/root/.local`. Stage `runtime` bắt đầu từ một base slim riêng, copy dependency đã cài cùng mã ứng dụng và chạy dưới user `appuser`. Base slim và việc bỏ các layer chứa công cụ build giúp giảm dung lượng image. [production/Dockerfile](02-docker/production/Dockerfile)

Kết quả `docker images my-agent` trên Docker Engine 28.5.1 được ghi dưới đây.

| Image | Image ID | SIZE do Docker hiển thị |
| --- | --- | ---: |
| `my-agent:develop` | `8c3bc2f0d252` | 1.67 GB |
| `my-agent:advanced` | `cba0341519f8` | 240 MB |

**Mức giảm khoảng 85,6%** theo số đã làm tròn trong cột `SIZE`, tính bằng `(1670 − 240) / 1670 × 100` sau khi đổi 1,67 GB thành 1.670 MB.

Container advanced chạy riêng trả HTTP `200` cho `POST /ask` với JSON `{"question":"What is Docker?"}`. Body trả cùng câu trả lời mock như bản develop. `docker exec <container> id -un` trả `appuser`.

### Exercise 2.4 — Docker Compose qua Nginx

```mermaid
flowchart LR
    client(["Client curl"])
    subgraph compose_net["Mạng bridge internal"]
        nginx["Nginx :80"]
        agent["FastAPI agent :8000"]
        redis[("Redis :6379")]
        qdrant[("Qdrant :6333")]
        nginx -->|"HTTP proxy"| agent
        agent -.->|"REDIS_URL và depends_on"| redis
        agent -.->|"QDRANT_URL và depends_on"| qdrant
    end
    client -->|"HTTP localhost:80"| nginx
```

> **Ý nghĩa kỹ thuật** — Nginx nhận HTTP từ máy host và chuyển tiếp đến agent theo tên service trên mạng Compose. Agent đợi Redis và Qdrant báo healthy trước khi khởi động. Hai đường đứt biểu thị cấu hình và phụ thuộc khi khởi động. Các request thử đi qua Nginx và được trả lời bằng mock LLM, nên lượt thử xác nhận luồng HTTP và trạng thái stack. [docker-compose.yml](02-docker/production/docker-compose.yml) · [nginx.conf](02-docker/production/nginx/nginx.conf) · [main.py](02-docker/production/main.py#L57-L64)

Chạy từ `02-docker/production/` sau khi tạo `.env.local` rỗng.

```bash
docker compose -p k5-day14-docker up -d --build --wait --wait-timeout 180
docker compose -p k5-day14-docker ps
curl -i http://localhost/health
curl -i -X POST http://localhost/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Explain microservices"}'
```

`docker compose ps` cho thấy `agent`, `redis` và `qdrant` đều `running (healthy)`, còn `nginx` đang `running`.

**`GET /health` qua Nginx** (trích output)

```http
HTTP/1.1 200 OK
Server: nginx
Content-Type: application/json

{"status":"ok","uptime_seconds":4.3,"version":"2.0.0","timestamp":"2026-11-25T10:29:46.622550"}
```

**`POST /ask` qua Nginx** (trích output)

```http
HTTP/1.1 200 OK
Server: nginx
Content-Type: application/json

{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

Đã chạy `docker compose -p k5-day14-docker down` và kiểm tra còn 0 container của project. Compose báo thuộc tính `version` đã cũ và bỏ qua thuộc tính đó. Stack vẫn khởi động và trả kết quả như trên.

## Part 3 — Cloud Deployment (CP6)

### Exercise 3.1–3.2 — Deploy agent Part 6

Đã deploy agent Part 6 từ commit `af2ece2` lên Render Free tại Ohio, với Key Value tương thích Redis qua mạng nội bộ. URL public là [day14-production-agent-0m8h.onrender.com](https://day14-production-agent-0m8h.onrender.com).

| Phép kiểm qua URL public | HTTP thực tế |
| --- | ---: |
| `GET /health` | `200` |
| `GET /ready` | `200` |
| `POST /ask` thiếu API key | `401` |
| `POST /ask` với API key hợp lệ | `200` |

Lệnh tái hiện các phép kiểm, thông tin cấu hình và ba ảnh nằm trong [DEPLOYMENT.md](DEPLOYMENT.md). Phép kiểm URL public trong checker gốc xác nhận `GET /health` trả `200`.

| Hạng mục | Railway | Render |
| --- | --- | --- |
| Build và khởi động | `railway.toml` chọn builder `DOCKERFILE`. Khi kết nối repo, cấu hình thư mục nguồn và đường dẫn config của service. | `render.yaml` khai báo web service Docker và chỉ rõ Dockerfile cùng build context trong `06-lab-complete/`. |
| Healthcheck và cổng | `healthcheckPath = "/health"` trong khối `[deploy]`. | `healthCheckPath: /health` trên web service. |
| Redis và secret | Tạo Redis cho project rồi đặt `REDIS_URL` và `AGENT_API_KEY` trong biến môi trường của agent. | Blueprint khai báo Key Value, tham chiếu connection string bằng `fromService` và tạo `AGENT_API_KEY` bằng `generateValue`. |

Cả hai dùng lệnh khởi động trong Dockerfile, đọc cổng từ `PORT`. [railway.toml](06-lab-complete/railway.toml) · [render.yaml](06-lab-complete/render.yaml) · [Railway Config as Code](https://docs.railway.com/config-as-code/reference) · [Render Blueprint YAML](https://render.com/docs/blueprint-spec)

### Exercise 3.3 — Pipeline Cloud Run

1. Cloud Build dùng image Python 3.11 để cài dependency cùng pytest, sau đó chạy `pytest tests/`.
2. Bước Docker build gắn tag `$COMMIT_SHA` và `latest`, rồi bước push đưa cả hai tag lên registry khai báo trong YAML.
3. Bước gcloud deploy image theo `$COMMIT_SHA` lên Cloud Run tại `asia-southeast1` và lấy `OPENAI_API_KEY` từ Secret Manager.
4. `service.yaml` mô tả cấu hình service, gồm 1–10 instance, tối đa 80 request đồng thời mỗi instance, cổng 8000 và probe `/health`, `/ready`.

[cloudbuild.yaml](03-cloud-deployment/production-cloud-run/cloudbuild.yaml) · [service.yaml](03-cloud-deployment/production-cloud-run/service.yaml)

## Part 4 — API Security

### Exercise 4.1 — API key ở bản develop

Chạy hai ví dụ bằng Docker từ Ubuntu WSL2, dùng image `my-agent:develop` đã build ở CP2 làm môi trường Python tạm. Mỗi container chạy `app.py` của đúng thư mục mẫu trên `127.0.0.1:8000`. Bản develop dùng API key tạm qua biến môi trường. Dừng bản develop trước khi bật bản production và cài dependency theo `production/requirements.txt`.

Cả hai lệnh gửi `POST /ask` với JSON `{"question":"Hello"}`. Lệnh thứ hai thêm header `X-API-Key` hợp lệ. [develop/app.py dòng 33–51](04-api-gateway/develop/app.py#L33-L51)

**Thiếu API key**

```http
HTTP/1.1 401 Unauthorized
content-type: application/json

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

**Có API key hợp lệ**

```http
HTTP/1.1 200 OK
content-type: application/json

{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

### Exercise 4.2 — JWT ở bản production

`POST /auth/token` với tài khoản mẫu `student` trả HTTP `200`. Sau khi xác thực thông tin đăng nhập, server ký JWT chứa định danh người dùng, role, thời điểm phát hành và hạn dùng. Client gửi JWT qua `Authorization: Bearer <token>` khi gọi `/ask`. Server xác minh chữ ký và hạn dùng trước khi dùng role và định danh từ token. [auth.py dòng 35–70](04-api-gateway/production/auth.py#L35-L70)

**Phản hồi cấp token đã che JWT và phần JWT lặp lại trong `hint`**

```text
HTTP/1.1 200 OK
{"access_token": "[REDACTED]", "token_type": "bearer", "expires_in_minutes": 60, "hint": "[REDACTED]"}
```

### Exercise 4.3 — Sliding window và phản hồi 429

Gửi liên tiếp 20 request `POST /ask` bằng JWT của `student` trong cùng một cửa sổ thời gian. Request **1–10 trả `200`**, còn request **11–20 trả `429`**. Số lượt còn lại trong body giảm từ `9` ở request đầu xuống `0` ở request thứ 10.

**Request 1 trong vòng lặp**

```http
HTTP/1.1 200 OK
content-type: application/json

{"question":"Explain JWT","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}
```

**Request 11, lần đầu bị giới hạn**

```http
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 1795602821
retry-after: 59
content-type: application/json

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

Bộ giới hạn dùng **sliding window log** với một `deque` timestamp trong RAM cho mỗi username. Trước mỗi request, nó bỏ timestamp cũ hơn 60 giây và đếm các lượt còn trong cửa sổ. Nếu đã đủ giới hạn, ứng dụng trả `429` và `Retry-After` tính theo thời điểm lượt cũ nhất hết cửa sổ. Nếu còn chỗ, nó ghi timestamp mới. Role `user` được 10 lượt/60 giây, role `admin` đã xác thực được 100 lượt/60 giây và vẫn chịu giới hạn. State hiện thuộc từng tiến trình, nên nhiều worker cần kho dùng chung để áp cùng một hạn mức. [rate_limiter.py dòng 16–87](04-api-gateway/production/rate_limiter.py#L16-L87) · [app.py dòng 138–145](04-api-gateway/production/app.py#L138-L145)

### Exercise 4.4 — Cost guard

- Bản mẫu kiểm ngân sách **sau rate limit và trước khi gọi mock LLM**. Mỗi người dùng có ngưỡng **1 USD/ngày** và log cảnh báo từ 80%. Khi chi phí đã đạt ngưỡng cá nhân, request tiếp theo nhận `402`. Nếu tổng chi phí trong tiến trình đạt ngưỡng global **10 USD**, kiểm tra global ưu tiên trả `503`. [app.py dòng 138–154](04-api-gateway/production/app.py#L138-L154) · [cost_guard.py dòng 40–91](04-api-gateway/production/cost_guard.py#L40-L91)
- Sau khi gọi mock LLM, app cộng số token đầu vào và đầu ra ước tính. Chi phí được tính riêng cho hai loại token rồi cộng lại theo đơn giá cố định trong code. `GET /me/usage` ghi nhận **10 request**, **40 input token**, **320 output token**, **0,000198 USD** đã dùng và **0,999802 USD** ngân sách còn lại. Request bị `429` bị chặn trước bước ghi usage. Trường `usage.budget_remaining_usd` trong `POST /ask` đang trả số **đã dùng**, còn trường cùng tên trong `GET /me/usage` trả số **còn lại**. Trong lần chạy này chưa chạm ngưỡng `402` hay `503`. [app.py dòng 147–168](04-api-gateway/production/app.py#L147-L168) · [cost_guard.py dòng 19–36](04-api-gateway/production/cost_guard.py#L19-L36) · [cost_guard.py dòng 93–124](04-api-gateway/production/cost_guard.py#L93-L124)
- Để dùng cho nhiều worker, lưu số tiền theo người dùng và kỳ ngân sách trong Redis, đặt TTL để dọn kỳ cũ. Với bài tập ngân sách tháng, dùng khóa theo `user_id` và `YYYY-MM`, tính số đã dùng cộng chi phí dự kiến rồi mới cho phép request. Thực hiện kiểm tra và giữ chỗ ngân sách trong cùng thao tác nguyên tử, sau đó đối soát theo lượng token thực tế. Bản mẫu CP3 lưu trong RAM, tạo lại record theo ngày cho từng user và chưa làm mới bộ đếm global khi sang ngày mới. [Exercise 4.4](CODE_LAB.md#exercise-44-cost-guard) · [cost_guard.py dòng 49–58](04-api-gateway/production/cost_guard.py#L49-L58)

## Part 5 — Scaling & Reliability

### Exercise 5.1 — Liveness và readiness

Liveness trả lời tiến trình còn phục vụ được hay không. Readiness trả lời replica có các phụ thuộc cần thiết để nhận traffic hay không. Khi mất Redis sau lúc khởi động, bản production vẫn trả `200` ở `/health` với trạng thái `degraded`, còn `/ready` trả `503`. Compose dùng `/health` làm container healthcheck. Hệ thống điều phối có thể dùng `/ready` để tạm ngừng đưa request tới replica khi Redis gián đoạn. [production/app.py dòng 187–215](05-scaling-reliability/production/app.py#L187-L215) · [docker-compose.yml dòng 32–41](05-scaling-reliability/production/docker-compose.yml#L32-L41)

### Exercise 5.2 — Graceful shutdown

Khi nhận SIGTERM, server ngừng nhận kết nối mới, cho request đang xử lý thời gian hoàn tất rồi chạy hook shutdown để dọn tài nguyên trước khi hết thời gian chờ. Bản develop minh họa việc hạ cờ readiness và theo dõi request đang chạy. Trong stack production, Uvicorn chạy trực tiếp trong container và gọi hook FastAPI khi tắt. [develop/app.py dòng 41–66](05-scaling-reliability/develop/app.py#L41-L66) · [production/app.py dòng 93–99](05-scaling-reliability/production/app.py#L93-L99) · [Dockerfile](05-scaling-reliability/production/Dockerfile)

### Exercise 5.3 — Session stateless nhờ Redis

Client gửi lại cùng `session_id` cho các lượt tiếp theo. Mỗi replica đọc và ghi cùng khóa `session:<session_id>` trên Redis. Mỗi lần ghi đặt TTL 3.600 giây và lịch sử giữ tối đa 20 tin nhắn. Nhờ đó, request sau có thể đến một replica khác mà vẫn tiếp tục được cuộc trò chuyện. Nếu Redis chưa kết nối được lúc khởi động, bản mẫu có chế độ fallback lưu RAM riêng từng tiến trình. Lịch sử ở chế độ đó chỉ có trên replica đã ghi nó. [production/app.py dòng 34–90](05-scaling-reliability/production/app.py#L34-L90) · [production/app.py dòng 128–169](05-scaling-reliability/production/app.py#L128-L169)

### Exercise 5.4 — Chạy ba replica qua Nginx

Trong `05-scaling-reliability/production/`, tạo `.env.local` rỗng rồi chạy các lệnh sau trong Ubuntu WSL2.

```bash
docker compose -p k5-day14-scaling up -d --build --scale agent=3 --wait --wait-timeout 180
docker compose -p k5-day14-scaling ps
python3 test_stateless.py
docker compose -p k5-day14-scaling logs agent
```

Compose báo **3 agent healthy**, **Redis healthy** và **Nginx đang chạy**. Nginx nhận request ở `localhost:8080` và chuyển tiếp đến các replica theo tên service `agent:8000`. Các agent và Redis giao tiếp trên mạng nội bộ của Compose. [docker-compose.yml](05-scaling-reliability/production/docker-compose.yml) · [nginx.conf](05-scaling-reliability/production/nginx.conf)

| Probes qua Nginx | Redis đang chạy | Sau khi dừng Redis |
| --- | --- | --- |
| `GET /health` | HTTP `200`, `status=ok`, `redis_connected=true` | HTTP `200`, `status=degraded`, `redis_connected=false` |
| `GET /ready` | HTTP `200`, `ready=true` | HTTP `503`, `{"detail":"Redis not available"}` |

Một lượt gọi `/ready` sau khi dừng Redis hết thời gian chờ khi đặt giới hạn 10 giây cho curl. Lượt kiểm tra lại cho phép chờ tối đa 50 giây và thu được HTTP `503` như trên.

Kiểm tra shutdown bổ sung bằng `docker stop --time 15` trên một replica sau khi hoàn tất các request. Docker ghi exit code `0` và log có các dòng sau.

```text
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:app:Instance instance-472a05 shutting down
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
```

Lượt này xác nhận Uvicorn hoàn tất vòng đời shutdown của replica đang rảnh. Kịch bản SIGTERM khi có request đang xử lý cần kiểm tra riêng ở CP5.

### Exercise 5.5 — Kết quả `test_stateless.py`

Cả 5 request `POST /chat` của cùng một session trả `200`. Bảng dưới đây lấy từ trường `served_by` mà script in ra. Log access của agent xác nhận cả ba replica đều đã xử lý request.

| Request | Replica phục vụ |
| ---: | --- |
| 1 | `instance-716f67` |
| 2 | `instance-1ea88a` |
| 3 | `instance-472a05` |
| 4 | `instance-716f67` |
| 5 | `instance-1ea88a` |

Khi script đọc lại session, API trả **10 tin nhắn**. Đọc trực tiếp khóa `session:<session_id>` bằng `redis-cli` cho kết quả `Stored messages: 10 user: 5 assistant: 5` và TTL còn **3598 giây** tại thời điểm đo. Năm lượt hỏi đáp vẫn nằm trong cùng một lịch sử dù được xử lý bởi ba replica khác nhau. Script gửi các lượt tuần tự và đọc lại lịch sử. Việc dừng replica ở trên diễn ra sau bài test. [test_stateless.py dòng 49–82](05-scaling-reliability/production/test_stateless.py#L49-L82)

Đã chạy `docker compose -p k5-day14-scaling down` và xác nhận còn **0 container** của project.

## Part 6 — Production-ready agent (CP5)

Chạy `python check_production_ready.py` đầy đủ từ `06-lab-complete/` trong Ubuntu WSL2 với Python 3.12.3 (`os.name=posix`) và Docker Engine 28.5.1. Checker tự khởi động Redis tạm và thoát với mã `0`.

### Checklist Deliverable

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

Các phép kiểm runtime ghi nhận image **56 MB theo phép đo của checker**, `429` sau 5 lượt với hạn mức 5 lượt/phút và vẫn `429` sau khi restart agent. Lượt thử giảm ngân sách trả `402`. Khi nhận SIGTERM trong lúc xử lý request, request trả `200` và tiến trình thoát với mã `0`. Phép kiểm `docker stop` báo mã `0` sau **0,9 giây**.

### Kiểm tra thêm qua Docker Compose

- Với cấu hình hai worker và cổng tùy chỉnh, cả `agent` và `redis` báo healthy. `/ask` trả `401` khi thiếu hoặc sai API key, và `422` khi câu hỏi chỉ gồm khoảng trắng.
- Gửi 12 request đồng thời với cùng API key và các `user_id` khác nhau, kết quả là **5 × `200` và 7 × `429`**. Các phản hồi `429` đều có `Retry-After`. Redis xử lý nguyên tử toàn bộ phép kiểm và ghi lượt trong cửa sổ 60 giây.
- Sau khi dừng Redis, `/health` trả `200` và `/ready` trả `503`. Đã dọn stack Compose thử nghiệm.

## AI log

- **CP0.** Dùng Codex để đối chiếu kế hoạch với tài liệu K5 và kiểm tra môi trường. Codex xác nhận Python trong Ubuntu là `3.12.3`, `os.name=posix`, container `hello-world` chạy được và GitHub báo repo Public. Tôi đã xác nhận CP0 trước khi chuyển sang CP1.
- **CP1.** Dùng Codex để chạy hai ví dụ, đối chiếu code và soạn câu trả lời Exercise 1.1–1.3. Các kết quả HTTP trong mục CP1 lấy từ lệnh chạy trong Ubuntu WSL2. Tôi đã xác nhận CP1 trước khi chuyển sang CP2.
- **CP2.** Sau khi tôi xác nhận CP1, dùng Codex để build hai image, đọc số đo từ `docker images`, kiểm tra container và stack Nginx, rồi ghi kết quả cùng sơ đồ Compose. Số đo và output HTTP lấy từ lượt chạy trong Ubuntu WSL2. Tôi đã xác nhận CP2 trước khi chuyển sang CP3.
- **CP3.** Dùng Codex để chạy các ví dụ API key và JWT, ghi kết quả HTTP đã che token, đọc implementation và giải thích rate limit cùng cost guard. Codex đối chiếu từng mã HTTP với kết quả chạy thực tế. Tôi đã xác nhận CP3 trước khi chuyển sang CP4.
- **CP4.** Dùng Codex để chạy Compose với ba replica, đối chiếu `served_by` và lịch sử trong Redis, kiểm tra hai probe và xem log shutdown. Kết quả được lấy từ các lệnh thực tế trong Ubuntu WSL2. Tôi đã xác nhận CP4 trước khi chuyển sang CP5.
- **CP5.** Dùng Codex để đọc hợp đồng Part 6, hoàn thiện các TODO và giải thích cơ chế auth, rate limit, cost guard, health/readiness và shutdown. Codex chạy checker gốc đầy đủ trong WSL2 có Docker và kiểm tra thêm luồng Compose với 12 request đồng thời. Tôi đã xác nhận CP5 trước khi chuyển sang CP6.
- **CP6.** Dùng Codex để so sánh cấu hình Railway và Render, đọc pipeline mẫu Cloud Run, triển khai agent cùng Key Value và chạy bốn lệnh curl từ Ubuntu WSL2. Tôi đăng nhập Render và trao lại quyền điều khiển. Codex xác minh kết quả với mã HTTP thật, kiểm tra ảnh để tránh lộ secret và ghi thông tin vào `DEPLOYMENT.md`. Phần CP6 đang chờ tôi kiểm tra trước khi sang CP7.
