# AirMorse

AirMorse là bàn phím Morse không chạm. Webcam và MediaPipe theo dõi bàn tay; bạn chụm ngón tay với ngón cái để nhập dấu chấm, dấu gạch, khoảng trắng, xóa, xuống dòng hoặc nhấn Enter. Chữ hiện trong ứng dụng. Khi bật gửi phím, ký tự đã giải mã được gõ vào cửa sổ đang chọn.

Hình từ webcam được xử lý trên máy. Ứng dụng không tải video lên mạng. Internet chỉ dùng để tải lại mô hình bàn tay nếu tệp cục bộ bị thiếu.

## Tính năng

- Hình webcam và khung xương bàn tay, lật ngang cho dễ nhìn.
- Ghi nhận chữ tắt khi mới mở. Bật bằng nút hoặc bằng cử chỉ like; tắt bằng nút hoặc like úp xuống.
- Giải mã Morse quốc tế cho A–Z và 0–9, sau một khoảng dừng.
- Xuống dòng bằng chuỗi `.-.-` (Shift+Enter). Chụm ngón trỏ và ngón giữa nhấn Enter, nên ô chat sẽ gửi tin.
- Chữ in hoa hoặc in thường. Chữ số không đổi.
- Âm báo cho chấm, gạch, ký tự và chuỗi không hợp lệ, nếu máy có loa.
- Bàn phím ảo, dòng chữ đã giải mã, nút chép và bảng mã Morse.
- Cửa sổ thu gọn nổi ở góc màn hình, không chiếm tiêu điểm bàn phím.
- Ghim cửa sổ lên trên và gửi phím sang ứng dụng khác.
- Lưu ngưỡng, thời gian chờ, kiểu chữ, ghim cửa sổ và gửi phím vào `config.json`.

## Yêu cầu

- Windows và Python 3.12.
- Webcam.
- Loa là tùy chọn. Không có âm thanh thì chữ vẫn hiện trên màn hình.

## Cài đặt và chạy

Mở PowerShell tại thư mục dự án:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Có thể chạy bằng `python -m airmorse`.

Mô hình nằm ở `models/hand_landmarker.task`. Nếu tệp thiếu hoặc quá nhỏ, AirMorse tải lại lúc khởi động và cần Internet.

## Cách dùng

1. Cho phép ứng dụng dùng camera nếu Windows hỏi: **Settings → Privacy & security → Camera**, bật quyền cho ứng dụng desktop.
2. Đưa cả bàn tay vào khung hình. Webcam vẫn chạy khi ghi nhận đang tắt.
3. Bật **Ghi nhận**. Ứng dụng luôn mở ở trạng thái tắt, nên cử chỉ lúc mới vào không thành chữ. Trạng thái này không được lưu; lần mở sau vẫn tắt.
4. Chụm đầu ngón với ngón cái, rồi thả:

   | Cử chỉ | Kết quả |
   | --- | --- |
   | Ngón cái lên, bốn ngón nắm lại, giữ khoảng một nhịp | Bật ghi nhận |
   | Ngón cái úp xuống, bốn ngón nắm lại, giữ khoảng một nhịp | Tắt ghi nhận |
   | Ngón trỏ | Chấm (`.`) |
   | Ngón giữa | Gạch (`-`) |
   | Ngón trỏ và ngón giữa cùng lúc | Enter (gửi tin trong ô chat) |
   | Ngón áp út | Dấu cách |
   | Ngón út | Xóa |

5. Ghép chấm và gạch của một chữ, rồi dừng. Mặc định chữ được gửi sau **0,8 giây** kể từ dấu cuối.
6. Nhập `.-.-` (chấm, gạch, chấm, gạch) rồi dừng để xuống dòng mà không gửi tin. AirMorse nhấn Shift+Enter. Notepad, Word và các ô chat đều hiểu đây là xuống dòng. Chuỗi này là ký hiệu xuống dòng trong Morse vô tuyến, không trùng A–Z hay 0–9.
7. Bật **Gửi phím vào cửa sổ khác**, rồi bấm vào Notepad hoặc trình duyệt trước khi ra dấu. AirMorse không gõ vào chính nó.
8. Bấm **Copy** để chép dòng chữ đã giải mã.

Ví dụ chữ **S** là ba lần ngón trỏ (`...`). Chữ **O** là ba lần ngón giữa (`---`). Lặp lại để được **SOS**.

Dấu cách giải mã chuỗi đang nhập trước, rồi mới thêm dấu cách. Enter cũng giải mã chuỗi đang nhập trước, rồi nhấn phím Enter. Trong Messenger, Zalo, Discord hay ChatGPT, phím Enter sẽ gửi tin. Muốn xuống dòng trong các ô đó thì dùng `.-.-`, không dùng cử chỉ hai ngón. Chuỗi không có trong bảng thì báo lỗi và không thêm cách, xuống dòng hay Enter. Xóa bỏ dấu cuối nếu chữ chưa xong; nếu không còn dấu nào, xóa ký tự cuối của dòng đã giải mã. Tắt ghi nhận giữ chữ đã có và bỏ dấu đang nhập dở.

## Cửa sổ thu gọn

Bấm **Chế độ Thu gọn**, hoặc nhấn `Ctrl+Shift+M`. Cửa sổ lớn ẩn đi; một khung nhỏ nổi ở góc màn hình, luôn nằm trên và không lấy tiêu điểm, nên vẫn gõ được sang ứng dụng khác.

Khung nhỏ có nút bật tắt ghi nhận, dòng chữ, nút **Sao chép** và nút **Phóng to**. Kéo khung để đổi chỗ; thả gần mép màn hình thì khung tự hút vào. Mở ngăn kéo để xem bảng mã Morse. `Ctrl+Shift+M` một lần nữa thì trở về cửa sổ lớn.

## Điều chỉnh

Các mục này nằm trong thẻ **Cài đặt & thiết lập** và được ghi vào `config.json` khi bạn đổi hoặc khi đóng ứng dụng.

- **Ngưỡng chụm**: độ gần giữa ngón cái và đầu ngón tay. Lớn hơn thì dễ nhận hơn; nhỏ hơn thì phải chụm sát hơn. Phạm vi `0.08–0.40`, mặc định `0.18`.
- **Thời gian chờ**: thời gian sau dấu cuối trước khi giải mã. Phạm vi `0.5–1.5` giây, mặc định `0.8` giây.
- **In hoa**: bật thì chữ mới là hoa, tắt thì chữ mới là thường. Chữ đã có không bị đổi, nên có thể trộn hoa và thường. Mặc định là bật.
- **Ghim lên trên**: giữ cửa sổ AirMorse phía trên các cửa sổ khác.
- **Gửi phím vào cửa sổ khác**: gõ chữ đã giải mã, dấu cách, xuống dòng, Enter và xóa vào cửa sổ đang chọn.

Camera mặc định là số `0`. Máy có nhiều camera thì sửa `camera_index` trong `config.json` rồi chạy lại.

## Bảng mã Morse

A–Z và 0–9 hiện trong cửa sổ, bốn cột. Dấu câu và ký tự ngoài bảng này chưa có. Xuống dòng dùng chuỗi `.-.-`, ghi riêng bên cạnh bảng.

## Kiểm thử

```powershell
pytest
```

Thư mục `tests/` kiểm tra giải mã Morse, chụm ngón, like, cấu hình, khung hình, cửa sổ, cửa sổ thu gọn và gửi phím. Kiểm thử bộ theo dõi tay cần MediaPipe và tệp mô hình; thiếu thì kiểm thử đó được bỏ qua.

## Cấu trúc

```text
airmorse/
  gesture/   Chụm ngón, like, máy trạng thái và giải mã Morse
  output/    Âm báo và gửi phím
  ui/        Cửa sổ chính, bàn phím ảo và cửa sổ thu gọn
  vision/    Camera, MediaPipe, khung hình và khung xương
models/      Mô hình hand landmarker
tests/       Kiểm thử
main.py      Điểm chạy
```

## Khi gặp lỗi

- **Không có hình**: cắm webcam, cấp quyền camera cho ứng dụng desktop, đóng Zoom, Teams hoặc trình duyệt đang giữ camera. Mặc định là camera `0`.
- **Không nhận chụm**: đưa cả bàn tay vào hình, tăng sáng, kéo **Ngưỡng chụm** lên. Ngưỡng cao dễ nhận nhầm.
- **Like không bật ghi nhận**: nắm bốn ngón lại, giơ ngón cái thẳng lên hoặc úp thẳng xuống, và giữ khoảng một nhịp. Bàn tay xòe hoặc chỉ chạm ngón trỏ không tính là like.
- **Chat bị gửi nhầm khi muốn xuống dòng**: dùng `.-.-`, không chụm ngón trỏ với ngón giữa. Cử chỉ hai ngón là phím Enter.
- **Không nghe tiếng**: kiểm tra loa. Chữ vẫn hiện khi không có âm thanh.
- **Không gõ sang ứng dụng khác**: bật **Gửi phím vào cửa sổ khác** và chọn cửa sổ đích. Chỉ chữ đã giải mã, cách, xuống dòng, Enter và xóa được gửi.
- **Không tải được mô hình**: kiểm tra `models/hand_landmarker.task`. Cần tải lại thì nối Internet và chạy lại.
