# Huyền Học AI

Ứng dụng tham khảo/giải trí gồm API FastAPI, SQLite, nhiều tài khoản đăng nhập, lịch vạn niên, lá số Tử Vi giản lược, dashboard feedback, SSE, Telegram tùy chọn, PWA, Tarot, Kinh Dịch, chia sẻ có thể thu hồi, PDF và thử nghiệm A/B.

> Các chỉ số và diễn giải không phải dự đoán khoa học, không thay thế tư vấn chuyên môn, y tế, pháp lý hoặc tài chính. Lịch âm sử dụng UTC+7; một số cách tính tiết khí, giờ hoàng đạo, cung phi và an sao Tử Vi được giản lược, có thể khác các trường phái.

## Yêu cầu

- Python 3.10 trở lên
- [Ollama](https://ollama.com/download)
- Secret JWT tối thiểu 32 byte

## Cài đặt và chạy

Trên Windows, có thể khởi động ứng dụng local bằng một lệnh PowerShell từ thư mục gốc:

```powershell
.\start.ps1
```

Script tạo virtual environment, cài dependencies, khởi động Ollama nếu cần, tải model `qwen2.5:7b` khi chưa có, rồi chạy API. Lần đầu có thể mất thời gian tải model. Mở <http://localhost:8000/> và giữ cửa sổ PowerShell mở; nhấn `Ctrl+C` để dừng backend. Secret đăng nhập local được lưu trong `.env.local` (gitignored) để không đổi mỗi lần chạy. Nếu cần dùng Telegram, script đọc `TELEGRAM_BOT_TOKEN` từ `.env.local`, rồi fallback sang `deploy/.env.prod`; hãy đặt token bot hợp lệ trong một trong hai file riêng này. Cần cài Python 3.10+ và Ollama trước.

Tính năng thời tiết/AQI là tùy chọn: đặt `OPENWEATHER_API_KEY` trong `.env.local`, `deploy/.env.prod` hoặc biến môi trường trước khi khởi động. Người dùng phải chủ động nhập tọa độ và đồng ý gửi chúng tới OpenWeather; tọa độ không được lưu. Trên trang Bản đồ, độ cao cũng là tùy chọn và chỉ gửi tới Google Maps Elevation API khi người dùng đánh dấu đồng ý; cần cấu hình `GOOGLE_MAPS_API_KEY`.

Tải model Ollama:

```powershell
ollama pull qwen2.5:7b
```

Cài dependencies và chạy API từ thư mục gốc repo (giữ biến môi trường secret trong cùng cửa sổ PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
$env:HUYEN_HOC_SECRET_KEY = (& python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:OLLAMA_MODEL = "qwen2.5:7b"
python -m uvicorn main:app --app-dir backend --reload --port 8000
```

Mở <http://localhost:8000/> để đăng ký/đăng nhập. Sau khi đăng nhập, các trang chính là `/app`, `/tu-vi` và `/dashboard`. Tài liệu API có tại <http://localhost:8000/docs>. Chạy frontend qua backend cùng origin để token Bearer được gửi đúng cách; không mở các trang HTML trực tiếp từ file.

Cấu hình bằng các biến môi trường `HUYEN_HOC_SECRET_KEY`, `OLLAMA_MODEL`, `OLLAMA_URL`, `OLLAMA_NUM_CTX` (mặc định 8192, giới hạn 512–32768) và `CORS_ORIGINS` (origin phân tách bằng dấu phẩy). Ứng dụng gửi giới hạn context theo từng request Ollama, thay vì phụ thuộc giá trị context toàn cục lớn của server. Không dùng lại JWT secret giữa môi trường hoặc công khai secret; nếu mất secret, token hiện có sẽ không còn hợp lệ.

Form phân tích hỗ trợ họ tên tùy chọn và giờ sinh địa phương (0–23). Chúng được lưu trong hồ sơ riêng của tài khoản như ngày sinh hiện tại; bỏ trống ở lần phân tích sau sẽ giữ giá trị đã có. Số tên theo bảng chữ cái Latin và Can Chi giờ chỉ là quy ước văn hóa/giải trí, không phải đánh giá tính cách hay dự đoán. Giờ sinh không hiệu chỉnh theo múi giờ/địa điểm; Ngũ cách không được tính từ chữ Latin vì cần dữ liệu nét chữ Hán. Bốn ngôn ngữ `vi`, `en`, `zh`, `ja` hiện áp dụng cho điều hướng và form hồ sơ chính; nội dung các module còn lại có thể vẫn bằng tiếng Việt.

## API

- Các trang sau đăng nhập gồm `/phong-thuy`, `/su-kien`, `/timeline-vi-mo`, `/ban-do`, `/gia-dao`, `/kinh-te`, `/trach-cat`, `/tam-linh`, `/video` và `/so-sanh`.
- `POST /api/phong-thuy/phan-tich`, `/api/phong-thuy/llm-tu-van` — Bát Trạch tham khảo và diễn giải Ollama; `GET /api/phong-thuy/phi-tinh` — sao năm giản lược.
- `GET/POST/DELETE /api/su-kien` — quản lý lịch riêng tư theo tài khoản; `/api/su-kien/tuan` và `/api/su-kien/dai-han` chỉ tổng hợp sự kiện do người dùng nhập.
- `GET /api/vi-mo/timeline` — mốc tiết khí nội bộ xấp xỉ, không phải nguồn tin tức hoặc cảnh báo thời tiết.
- `POST /api/moi-truong/hien-tai` — thời tiết/AQI theo tọa độ; cần `OPENWEATHER_API_KEY`. Tọa độ chỉ chuyển tới OpenWeather khi người dùng chủ động đồng ý truy vấn và không được lưu trong hồ sơ.
- `POST /api/tong-the` — tổng hợp phong thủy, lịch cá nhân, mốc tiết khí và (nếu chủ động nhập tọa độ) dữ liệu môi trường.
- `POST /api/ban-do/phan-tich` — hiển thị vị trí đã nhập và thông tin độ cao tùy chọn; hướng mặt tiền phải do người dùng nhập, tọa độ không lưu. Google Maps chỉ được gọi khi có opt-in và API key.
- `POST /api/gia-dao/phan-tich` — nhóm cung phi/hướng tham khảo tối đa 10 thành viên; ngày sinh không lưu và không chấm điểm hòa hợp.
- `GET /api/kinh-te/thi-truong` — quan sát VN-Index và tỷ giá USD/VND từ nguồn công khai; có thể bị trễ/không sẵn có, không phải tư vấn đầu tư.
- `POST /api/trach-cat/tim-ngay` — tra ngày theo lịch dân gian giản lược cho các hoạt động phổ thông; không dùng để trì hoãn chăm sóc y tế hoặc nghĩa vụ.
- `GET /api/tam-linh/thoi-khoa` — gợi ý thực hành chánh niệm tự chọn, không chẩn đoán hoặc điều trị.
- `POST /api/tu-vi-tay/chart` — cung Mặt Trời tham khảo theo ngày sinh; không giả lập Mặt Trăng/cung Mọc.
- Trang `/video` tạo video WebM hoàn toàn trong trình duyệt; nội dung không tải lên server, không hỗ trợ MP4.
- `POST /api/analyze` — phân tích ngày sinh hợp lệ, lưu hồ sơ và kết quả.
- Schema phân tích ngày sinh nhận thêm `gio_sinh` tùy chọn (0–23); kết quả hồ sơ có chỉ số tên/giờ sinh tham khảo khi được cung cấp.
- `GET /api/i18n`, `/api/i18n/{lang}` — từ điển tĩnh vi/en/zh/ja; giao diện chính lưu lựa chọn ngôn ngữ trong trình duyệt.
- `POST /api/analyze/stream` — stream metadata, token, lỗi và kết quả cuối qua SSE; yêu cầu Bearer token.
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` — tạo tài khoản, đăng nhập và lấy tài khoản hiện tại.
- `GET/PUT /api/auth/preferences` — đọc/cập nhật opt-in dataset, lịch Telegram hằng ngày và gửi kết quả phân tích Telegram.
- `GET /api/profiles` — danh sách tối đa 100 hồ sơ của tài khoản cùng kết quả diễn giải gần nhất (yêu cầu đăng nhập).
- `POST /api/telegram/link-code` — tạo mã Telegram dùng một lần, hết hạn sau 10 phút.
- `POST /api/feedback` — lưu đánh giá chỉ số/kết quả (0–100), có thể gắn scope.
- `GET /api/history/{ngay_sinh}` — xem feedback thuộc tài khoản hiện tại (`DD/MM/YYYY`).
- `POST /api/relearn/{ngay_sinh}` — tóm tắt feedback khi có ít nhất 3 mục.
- `/api/lich-van-nien/ngay`, `/tuan`, `/thang` — lịch tham khảo, yêu cầu Bearer token và hồ sơ.
- `POST /api/lich-van-nien/llm-tuan` — Ollama diễn giải tuần.
- `POST /api/tu-vi/lap-so`, `/api/tu-vi/luan-giai` — tạo lá số và diễn giải tham khảo.
- `POST /api/tu-vi/export-pdf` — xuất lá số PDF; có thể bật `luan_giai` để gọi Ollama.
- `POST /api/analyze/export-pdf` — xuất bản mệnh PDF và diễn giải bằng Ollama.
- `POST /api/hop-tuoi` — so sánh hai ngày sinh ISO-8601 bằng các chỉ số văn hóa giản lược.
- `POST /api/tarot` — rút ngẫu nhiên 1, 3 hoặc 5 lá; câu hỏi 5–500 ký tự, không lưu câu hỏi/trải bài.
- `POST /api/kinh-dich` — gieo sáu hào ngẫu nhiên bằng phương pháp ba đồng xu và xin diễn giải từ Ollama.
- `POST /api/share` — tạo liên kết hồ sơ đã lọc; trang công khai `/share/{token}` chỉ lộ dữ liệu đã cho phép.
- `GET /api/share/{token}`, `DELETE /api/share/{token}` — đọc liên kết công khai và thu hồi (chỉ chủ sở hữu được thu hồi).
- `POST /api/analyze/ab` — chạy phân tích A/B và liên kết feedback tới đúng prediction.
- `GET /api/ab/overview` — xem thống kê của tài khoản; `/api/admin/ab/overview` và `PUT /api/admin/ab/weights` yêu cầu ID quản trị đã cấu hình.
- `GET /api/dashboard/overview`, `/api/dashboard/raw-feedback` — thống kê dữ liệu feedback của người đăng nhập.

JWT cần cấu hình secret; password được băm bcrypt và giới hạn tối đa 72 byte. Mỗi hồ sơ được khóa theo tài khoản, và nhiều tài khoản có thể lưu cùng ngày sinh. Migration lúc khởi động mở rộng schema SQLite cũ; dữ liệu cũ không có chủ sở hữu vẫn ở trạng thái không gắn tài khoản, không tự chia sẻ cho user mới.

Feedback được đưa vào ngữ cảnh phân tích và tạo hệ số heuristic sau tối thiểu 5 mẫu/lĩnh vực; dashboard dùng MAE để mô tả feedback. Đây không phải huấn luyện model hay bằng chứng về độ chính xác dự đoán. SQLite mặc định lưu tại `backend/huyen_hoc.db`; có thể đổi bằng `HUYEN_HOC_DATABASE_URL`. Bản mẫu chưa có xác minh email hay khôi phục mật khẩu.

## Production với Docker

Ví dụ triển khai dùng một Uvicorn worker và SQLite trên volume bền vững. Cần máy chủ Linux có Docker Compose, domain trỏ tới máy chủ và cổng 80/443 mở. Caddy tự động cấp HTTPS; cấu hình thay thế Nginx có giới hạn tốc độ tích hợp nhưng cần chứng chỉ TLS được cài riêng. Caddyfile dùng Caddy chuẩn, không yêu cầu plugin rate-limit; hãy đặt rate limit/WAF ở edge nếu cần. Không expose API backend hoặc Ollama trực tiếp ra Internet.

```sh
cp deploy/.env.prod.example deploy/.env.prod
# Thay DOMAIN/CORS_ORIGINS, sinh HUYEN_HOC_SECRET_KEY ngẫu nhiên >= 32 byte.
# Chỉ thêm ADMIN_USER_IDS (ID số từ /api/auth/me) nếu cần quản trị A/B.
cd deploy
sh deploy.sh
```

Script đợi API và Ollama sẵn sàng, rồi tự tải model `OLLAMA_MODEL` nếu chưa có. Không commit `deploy/.env.prod`; file đã nằm trong `.gitignore`. Đổi secret sẽ làm token đăng nhập hiện tại mất hiệu lực. Backend chạy một worker vì Telegram polling/scheduler và SQLite hiện không được thiết kế để chạy nhiều worker hoặc scale ngang. Backup volume `huyen_data` và kiểm tra restore trước khi nâng cấp; Ollama/model có volume riêng. `/health` kiểm tra API/DB và báo Ollama riêng ở trạng thái `degraded`/`unreachable`, không trả chi tiết lỗi; healthcheck container chỉ phụ thuộc API/DB. OpenAPI/Swagger bị tắt khi `APP_ENV=production`.

WeasyPrint cần thư viện đồ họa hệ thống; Dockerfile cài Pango, HarfBuzz và font tiếng Việt. Trên Windows, cài các gói Python chưa đủ nếu thiếu DLL/native libraries phù hợp. Nếu PDF không khả dụng, API trả lỗi 503.

Liên kết chia sẻ chứa token ngẫu nhiên chỉ lưu dạng hash trong database, mặc định hết hạn sau 30 ngày và có thể thu hồi. Nội dung công khai không gồm tên/ngày sinh; lá số tùy chọn cũng đã lược bỏ ngày sinh. Tarot/Kinh Dịch không lưu câu hỏi hay kết quả; diễn giải gửi câu hỏi tới Ollama đã cấu hình. Hợp tuổi chỉ chạy phép tính cục bộ.

### Cloudflare Worker (tùy chọn)

Worker cấu hình tại `deploy/cloudflare/wrangler.jsonc` chuyển tiếp tới backend HTTPS, giới hạn yêu cầu API bằng Rate Limiting bindings và không cache response hồ sơ/API. CORS chỉ cho phép các origin khai báo; Worker loại bỏ header chuyển tiếp do client tự gửi và không ghi body/token/IP vào log. Nếu binding giới hạn tạm thời lỗi, Worker từ chối request. Rate Limiting binding là biện pháp giảm tải theo điểm hiện diện, không thay thế quota/billing chính xác.

Trước khi triển khai, xác nhận quyền quản lý zone `huyenbao.com`, backend thật ở `https://api.huyenbao.com`, TLS hợp lệ và firewall/origin chỉ nhận lưu lượng Cloudflare hoặc dùng Cloudflare Tunnel để tránh bypass Worker. Thay ba `namespace_id` mẫu bằng số nguyên chưa dùng trong tài khoản Cloudflare và cấu hình đúng `CORS_ALLOWED_ORIGINS`. Cần Wrangler 4.36.0 trở lên. Kiểm tra Worker bằng `node --test deploy/cloudflare/worker.test.js`; chỉ chạy `wrangler deploy` sau khi xác nhận đúng tài khoản/zone và môi trường đích. Worker chưa được deploy hay gắn với tài khoản/domain thật trong thay đổi này. Thanh toán, tự đăng bài mạng xã hội, NFT, voice AI, LMS và ứng dụng di động vẫn được hoãn cho giai đoạn sau.

Thử nghiệm A/B chỉ thay đổi hướng dẫn diễn đạt, gán biến thể ổn định theo tài khoản/nhiệm vụ và không xem feedback là “nhãn sự thật”. Reward chỉ được tạo khi feedback gắn với đúng prediction. Trọng số biến thể phải không âm, có tổng dương, được chuẩn hóa và cập nhật qua endpoint quản trị. Nếu `ADMIN_USER_IDS` trống thì không có tài khoản quản trị A/B.

## Streaming, Telegram và PWA

- Trang `/app` dùng SSE; metadata hồ sơ/chỉ số đến trước, token hiển thị bằng `textContent`, và prediction chỉ được lưu sau khi nhận JSON hoàn chỉnh. Endpoint vẫn yêu cầu đăng nhập.
- Telegram là tùy chọn. Đặt `TELEGRAM_BOT_TOKEN` trong môi trường backend (hoặc `deploy/.env.prod`, vốn đã được gitignore) để bật long polling và lịch gửi 07:00 hằng ngày, 20:00 Chủ nhật theo `Asia/Ho_Chi_Minh`. Không đặt token trong mã nguồn, tài liệu hoặc commit. Nếu token bị lộ, thu hồi/tạo token mới bằng BotFather và cập nhật secret triển khai ngay. Người dùng phải đăng nhập website, tạo mã liên kết rồi gửi `/link MA_CODE` trong chat riêng với bot. Website lưu hồ sơ và kết quả diễn giải theo tài khoản; mục “Hồ sơ đã lưu” cho phép nạp lại hồ sơ và kết quả gần nhất. Gửi kết quả qua Telegram là lựa chọn riêng, mặc định tắt; khi bật, toàn bộ hồ sơ (có thể gồm tên/ngày sinh) và kết quả được gửi dưới dạng tệp JSON tới Telegram đã liên kết. Thông báo kết quả không phụ thuộc lựa chọn nhận lịch hằng ngày. `/unlink` tắt cả hai loại thông báo và chỉ gỡ chat, không xóa tài khoản web. Chỉ chạy **một Uvicorn worker** khi bật polling/scheduler để tránh nhiều bot worker tranh update và gửi trùng lịch.
- PWA hoạt động trong secure context (HTTPS hoặc localhost). Service worker chỉ cache vỏ HTML tĩnh, manifest và icon; không cache `/api/`, query cá nhân hay token. Khi ngoại tuyến, màn hình nhắc rằng phân tích/lịch cá nhân cần server; chưa hỗ trợ đồng bộ nền.

## Dataset và LoRA ngoại tuyến

Mặc định feedback không được đưa vào dataset. Người dùng phải bật đồng ý ở trang `/app`; feedback cũ chỉ đủ điều kiện nếu được gắn với đúng `prediction_id`. Người vận hành cần kiểm tra phản hồi thủ công rồi mới duyệt từng ID bằng CLI. Chỉ các mẫu đã duyệt và còn consent mới được xuất; ngày sinh, tên, ghi chú, user/profile ID không được đưa vào JSONL, và mẫu có ngày sinh/tên nhận diện trực tiếp trong output sẽ bị bỏ qua. Đây là de-identification, không bảo đảm chống tái nhận diện tuyệt đối.

Từ thư mục gốc, bật consent ở UI trước, xem ID phản hồi trong dashboard/API lịch sử, rồi duyệt các ID đã kiểm tra:

```powershell
python -m backend.dataset_builder --approve-feedback-id 123 --approve-feedback-id 124
```

Export cần tối thiểu 5 mẫu (có thể đổi ngưỡng bằng `--minimum-examples`) và ghi atomic vào `finetune/dataset/`, thư mục này đã được gitignore. Bộ dữ liệu chỉ chứa cặp feedback–prediction liên kết chính xác và yêu cầu duyệt thủ công. Feedback là đánh giá chủ quan, **không phải nhãn sự thật**; người duyệt phải xác nhận output phù hợp trước khi chấp thuận dùng làm target. Thu hồi consent ngăn các lần export sau và gỡ duyệt trong database; operator phải tự xóa an toàn JSONL, checkpoint hoặc model adapter đã xuất/training trước đó vì không thể đảo ngược việc huấn luyện.

Huấn luyện LoRA là tùy chọn riêng, không chạy trong API và không gửi dữ liệu tới dịch vụ bên ngoài do ứng dụng. Dùng một môi trường training riêng có đủ RAM/GPU:

```powershell
python -m pip install -r finetune\requirements-training.txt
python finetune\train_lora.py --base-model Qwen/Qwen2.5-7B-Instruct --dataset-dir finetune\dataset --output-dir finetune\output
ollama create huyen-hoc-qwen2.5 -f finetune\Modelfile
```

Hoặc chạy `finetune\train.ps1` sau khi đã duyệt dataset và cài gói training. Base model trong Modelfile phải tương thích với model dùng khi train; pipeline hiện chọn Qwen2.5 7B Instruct và LoRA target `q_proj`/`v_proj`. Không có subprocess huấn luyện hoặc quyền admin dựa trên tên tài khoản trong API.

## Kiểm thử

Từ thư mục `backend`, chạy:

```powershell
python -m unittest discover -s tests -v
```
