# AGENTS.md — Quy ước phối hợp nhiều AI agent

Tệp này được Cursor, Antigravity, Claude Code và các agent khác tự đọc khi mở dự án.
Mọi agent làm việc trên repo này PHẢI tuân theo quy trình dưới đây.

## Vai trò

| Agent | Vai trò |
| --- | --- |
| **Claude Code** | Điều phối chính: chia nhiệm vụ, viết spec, review và merge. |
| **Cursor** | Thực thi nhiệm vụ được giao (sửa code nhỏ–vừa, UI, refactor cục bộ). |
| **Antigravity** | Thực thi nhiệm vụ được giao (tính năng lớn hơn, chạy/thử ứng dụng, kiểm thử). |

## Quy trình

1. Nhiệm vụ nằm trong `.agents/TASKS.md`. Chỉ nhận nhiệm vụ có `owner` là tên của bạn và `status: todo`.
2. Khi bắt đầu: đổi `status` thành `doing`, tạo nhánh `agent/<owner>/<task-id>` từ `main`.
3. Chỉ sửa các tệp nằm trong phạm vi `files` của nhiệm vụ. Cần sửa thêm tệp khác → ghi vào handoff, không tự mở rộng.
4. Trước khi bàn giao, chạy `pytest` và đảm bảo tất cả đều qua.
5. Commit, push nhánh, rồi viết `.agents/handoffs/<task-id>.md` theo mẫu `.agents/handoffs/_TEMPLATE.md`.
6. Đổi `status` thành `review`. Claude Code sẽ review, rồi chuyển sang `done` hoặc `changes` kèm nhận xét.

## Tiết kiệm token

- Đọc spec trong `TASKS.md` và các tệp liệt kê trong `files` trước; không quét toàn bộ repo.
- Handoff ngắn gọn: thay đổi gì, vì sao, kết quả test, điểm còn nghi vấn. Không dán lại toàn bộ code.
- Không tạo tài liệu, tệp mẫu hay refactor ngoài phạm vi nhiệm vụ.

## Quy ước code

- Python 3.12, giữ phong cách hiện có trong `airmorse/` (type hints, tên rõ ràng, ít comment).
- Mỗi thay đổi hành vi cần kèm kiểm thử trong `tests/` (dùng fixture ở `tests/support.py` khi phù hợp).
- Không commit `config.json`, `.venv/` hoặc tệp mô hình mới.
