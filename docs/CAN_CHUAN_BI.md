# Những gì còn thiếu: bạn cần chuẩn bị

*(Cập nhật 30/10/2026. Giá và điều khoản hay thay đổi, hãy kiểm tra lại trên trang chính thức trước khi trả tiền.)*

## 0. Cập nhật mới nhất: chỉ cần bỏ file `.txt`
- Từ nay, đầu vào mặc định là kịch bản `input/<ten>.txt`. Pipeline tự gen giọng qua API AI84 (Eleven v4, có thẻ cảm xúc) và tự xuất SRT, nên không phải qua app gen voice và không tốn thêm một lần gen để lấy SRT.
- Ngôn ngữ đầu ra theo đúng kịch bản. Giọng mặc định: US là Brian, ES là Alberto Rodríguez, VI là Tung Dang. Muốn thêm ngôn ngữ thì đưa mình voice ID.
- Chi phí: khoảng 1 credit AI84 cho mỗi ký tự. Phim 45 phút tiếng Anh khoảng 40.000 ký tự, tức khoảng 40.000 credit AI84.
- Phần 1 bên dưới chỉ áp dụng khi bạn đã có sẵn WAV+SRT.

## 1. Lời đọc có sẵn WAV+SRT (không còn là mặc định)
- Bạn gen giọng trên **ai84.pro** bằng MiniMax Speech 2.8 HD, rồi bỏ cặp `input/<ten>.wav` + `<ten>.srt` cùng tên vào thư mục `input/`.
- **Xuất WAV 44,1 kHz** (MiniMax qua AI84 tối đa 44,1 kHz; 48 kHz cũng được), chỉ có giọng, không nhạc.
- SRT tạo bằng Whisper từ chính file WAV đó.
- Pipeline **không gen lại giọng**. Nó cắt ở chỗ lặng giữa các câu, chỉnh độ nghỉ theo cảm xúc, ghép lại và dời toàn bộ SRT theo nhịp mới.
  - Đã chạy thử trên file thật 38 phút: 712 đoạn, mọi điểm cắt đều nằm trong khoảng lặng, chạy mất khoảng 10 giây.
  - Mình **chưa nghe** bản ghép. Bạn nên nghe vài chỗ chuyển đoạn trước khi dùng.
- **Câu đọc sai:** tìm mã đoạn (ví dụ `U012`) trong `projects/<ten>/pacing.md`. Gen lại đúng đoạn chữ đó trên AI84 cùng giọng và tốc độ, lưu thành `projects/<ten>/voice/replace/U012.wav`, rồi chạy `assemble`. Không phải gen lại cả bài.
- Workflow **không gọi API AI84** và không đọc hay lưu key AI84 của bạn. Nếu muốn tự động gen lại câu lỗi qua API AI84, hãy nói, mình sẽ làm thêm sau.

## 1b. ElevenLabs: dùng cho SFX và nhạc (không dùng đọc giọng)
- Key `ELEVENLABS_API_KEY` đã có. Thư viện SFX dùng chung (72 file, có LICENSES.md) nằm ở `history-video-workflow/assets/sfx`. Phim mới dùng lại thư viện này, không gen lại để khỏi tốn credit.
- Lệnh xem số dư (miễn phí) đã chạy được: `doc.py doctor` báo gói Starter, đã dùng 6.034 trên 40.000 credit (ngày 30/10/2026). Mọi lần chạy thử đều đọc số dư thật trước khi hỏi bạn.
- **Nhạc nền mặc định là ElevenLabs Music**, xem mục 2.
- Phương án dự phòng: đọc giọng bằng ElevenLabs từ `script.txt`. Tốn khoảng 1 credit/ký tự, phim 45 phút khoảng 40.000 credit, tức trọn một kỳ của gói Starter (40.000 credit). Chỉ dùng khi bạn yêu cầu.

## 2. Nhạc nền: ElevenLabs Music là mặc định, Suno là tuỳ chọn thủ công
**ElevenLabs Music (mặc định, API chính thức, dùng chung key):**
- **Bản quyền:** ngày 30/10/2026 ElevenLabs đã xác nhận với bạn rằng giấy phép thương mại của gói **Starter** bao gồm Eleven Music trong video YouTube bật kiếm tiền, giống như SFX. Mỗi file nhạc sẽ được ghi một dòng trong `assets/music/LICENSES.md`.
- **Ngân sách:** gói Starter có 40.000 credit mỗi kỳ.
  - Thư viện 72 SFX chỉ tốn 6.034 credit, khoảng 10 credit cho mỗi giây âm thanh.
  - Ngày 30/10/2026 còn **33.966 credit**; kỳ mới bắt đầu ngày 30/11/2026.
  - Số dư thật luôn được đọc lại trong lần chạy thử, không dựa vào con số ghi ở đây.
- Vẫn nên dùng bộ nhạc nền chung, không gen theo từng cảnh, để tiết kiệm credit cho các phim sau.
- Vì vậy không gen nhạc cho từng cảnh. Thay vào đó gen **một bộ nhỏ "nhạc nền theo cảm xúc" dùng chung cho mọi phim**: căng thẳng, buồn, trận đánh, chiến thắng/khép lại, bí ẩn, hành quân, ai điếu. Mỗi loại 1–2 bản dài 60–120 giây, nhịp đều, để cắt và lặp theo ô nhịp.
- Một phim 40 phút chỉ cần ghép lại các bản này theo từng chương.
- **Trước khi gen**, agent luôn liệt kê từng bản (cảm xúc, prompt, thời lượng) cùng số credit ước tính, rồi **chờ bạn đồng ý**.
- Giá credit/giây của Music **chưa đo**. Agent sẽ thử một bản ngắn (hỏi bạn trước), đo số dư trước và sau, rồi mới ước tính cho cả bộ theo số đo thật.
- Nếu không đủ credit, agent chỉ gen những cảm xúc phim đang cần, hoặc chờ sang tháng.

**Suno (tuỳ chọn, làm tay):**
- Suno **chưa có API công khai** (tháng 10/2026).
- **Không dùng sunoapi.org** hay các "Suno API" không chính thức khác. Chúng vi phạm điều khoản của Suno và quyền sử dụng bài nhạc không rõ ràng. Key sunoapi.org bạn vừa tạo sẽ không được tích hợp; nên xoá hoặc không nạp tiền vào đó.
- Nếu muốn dùng Suno:
  - Mua Suno Pro. Bài tạo khi đang ở Pro/Premier mới được dùng thương mại; bài tạo ở gói Free thì không.
  - Agent viết prompt vào `projects/<phim>/music/PROMPTS.md`.
  - Bạn tạo nhạc trên suno.com, tải file vào `projects/<phim>/music/` và ghi lại link bài.

**Cách pipeline xử lý nhạc** (cả hai nguồn):
- Lên kế hoạch nhạc theo từng chương từ lời đọc.
- Dò beat, cắt và chuyển nhạc đúng phách mạnh.
- Tự hạ nhạc khi có giọng.
- Bản trộn cuối đạt −14 LUFS, đỉnh tối đa −1 dBTP.

## 3. Key miễn phí cho kho tư liệu (tuỳ chọn, nên có)
| Nguồn | Cần gì | Cách lấy |
|---|---|---|
| Wikimedia Commons, Library of Congress, Openverse, Internet Archive | không cần key | (agent tự ghi User-Agent kèm email liên hệ) |
| US National Archives (NARA) Catalog API | API key miễn phí | ⏳ đã gửi email, đang chờ trả lời |
| DVIDS (ảnh/video quân đội Mỹ, public domain) | API key miễn phí | ✅ `DVIDS_API_KEY` đã đặt và đã kiểm tra |
| Europeana | API key miễn phí | ⏳ đang chờ duyệt |

Đặt key vào biến môi trường User: `NARA_API_KEY`, `DVIDS_API_KEY`, `EUROPEANA_API_KEY`. File `key.txt` trong thư mục dự án đã được thêm vào `.gitignore`. Agent không đọc file này ra chat và không commit nó.

## 4. Bản đồ: không cần trả tiền, nhưng phải đúng giấy phép
| Lớp bản đồ | Nguồn và giấy phép | Lưu ý |
|---|---|---|
| Địa hình | AWS Terrain Tiles (công khai) hoặc Copernicus DEM | ghi nguồn |
| Ảnh vệ tinh | **Sentinel-2 cloudless 2016 của EOX (CC BY 4.0)** | Các năm 2018 trở đi là **CC BY-NC-SA, không dùng được** cho kênh kiếm tiền. Phim mẫu cũng dùng bản 2016 vì lý do này. |
| Biên giới | Natural Earth (public domain) | |
| Đường, sông, địa danh | OpenStreetMap (ODbL) | ghi "© OpenStreetMap contributors"; lấy dữ liệu qua Overpass, không tải hàng loạt tile từ tile.openstreetmap.org |

Bản đồ Việt Nam phải thể hiện Hoàng Sa, Trường Sa thuộc Việt Nam.

## 5. Ảnh và clip tư liệu: agent tự tìm, nhưng vẫn phải đúng bản quyền
- Agent tự tìm cả ảnh và clip ngắn trên Wikimedia Commons, DVIDS và Openverse; Google Images chỉ dùng làm gợi ý. Giấy phép luôn được đọc trên trang gốc của từng file.
- Bạn chỉ cần bỏ file vào khi có tư liệu riêng mà bạn đã có quyền dùng.
- Ảnh của **TTXVN, Trung tâm Lưu trữ Quốc gia III, Báo QĐND** có trong phim mẫu, nhưng **không mặc nhiên là tự do sử dụng**.
- Workflow chỉ dùng những ảnh này khi file cụ thể trên Wikimedia Commons có nhãn PD/CC hợp lệ, hoặc khi bạn có giấy phép. Nếu bạn có giấy phép, đặt file vào `input/<phim>/media/` kèm `RIGHTS.md`.
- Với kênh khán giả Mỹ nói về chiến tranh có Mỹ hoặc Pháp tham gia, **NARA, DVIDS và ECPAD** (cần xin phép) là nguồn phong phú hơn.
- **Không dùng:** IWM (giấy phép phi thương mại), Getty, AP, British Pathé khi chưa mua license.

## 6. Phần mềm và tài khoản khác
- ffmpeg, Python 3.12: máy đã có.
- Chạy `scripts/setup.ps1` để tạo `.venv`.
- Không cần tài khoản Goha AVS hay TOOL SY.

## 7. Phần chưa làm (theo thứ tự nên làm tiếp)
1. Trình dựng hình (`render.py`): ảnh, Ken Burns, chuyển cảnh, giọng → MP4 1080p.
2. Mẫu chữ trên hình: thẻ ngày, lower third, thẻ tiêu đề, thẻ số liệu, trích dẫn đánh máy.
3. Tìm và tải tư liệu kèm ghi giấy phép (`media`).
4. Bản đồ địa hình/vệ tinh có chú thích (`maps`).
5. Nhạc: thư viện nhạc nền ElevenLabs Music (chạy thử báo credit trước), nhập file Suno làm tay, dò beat, cắt đúng nhịp. Kèm khâu trộn (ducking, −14 LUFS, đỉnh tối đa −1 dBTP).
6. Đặt SFX theo từng chữ, dùng lại thư viện SFX ElevenLabs của dự án cũ.
7. Studio web nhiều track, chế độ góp ý (review notes) và MCP để Claude điều khiển. Ước tính 3–6 ngày công.
   - **Không trích xuất từ TOOL SY.** Editor "SyHQ studio" thực chất là mã của Revo Studio 1.2.0 đã đổi tên: chỉ còn bản React đã minify và file Python .pyc, mã nguồn gốc không còn. Bê nguyên sang vừa rủi ro bản quyền vừa mất nhiều tuần. Thay vào đó, ta chỉ học theo giao diện và cấu trúc dữ liệu của nó.
