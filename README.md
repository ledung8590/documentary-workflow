# documentary-workflow

Phim tài liệu tư liệu thật (ảnh/phim lưu trữ, bản đồ thật). Lời đọc bạn gen sẵn trên AI84/MiniMax, pipeline chỉnh lại nhịp ngắt nghỉ theo cảm xúc mà không gen lại giọng. Nhạc nền ElevenLabs Music (Suno tuỳ chọn) cắt theo beat, SFX đặt đúng chữ. Dự án anh em với `history-video-workflow` (hoạt hình chibi).

- Quy trình: `docs/WORKFLOW.md`
- Giọng và nhịp: `docs/VOICE.md`
- Kiến trúc: `docs/ARCHITECTURE.md`
- **Cần chuẩn bị gì: `docs/CAN_CHUAN_BI.md`**
- Trong Claude Code, mở thư mục này và gõ `/gendoc`.

```
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
.venv\Scripts\python.exe scripts\doc.py ingest              # input/<ten>.wav + <ten>.srt
.venv\Scripts\python.exe scripts\doc.py pace <phim>         # cắt ở chỗ lặng, nghỉ theo cảm xúc -> pacing.md
.venv\Scripts\python.exe scripts\doc.py assemble <phim>     # voice.wav + SRT đã dời + timeline.json
```
Test offline: `.venv\Scripts\python.exe -m pytest tests -q`.
