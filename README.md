# AirMorse

AirMorse là bàn phím Morse không tiếp xúc: ứng dụng dùng webcam và MediaPipe để theo dõi bàn tay, nhận diện thao tác chụm đầu ngón tay với ngón cái, rồi giải mã thành chữ hoặc số. Kết quả được hiển thị trong ứng dụng; bạn cũng có thể bật tùy chọn gửi phím vào cửa sổ đang được chọn.

## Tính năng

- Xem hình ảnh webcam và khung xương bàn tay theo thời gian thực.
- Nhận diện thao tác chụm ngón tay để nhập dấu chấm, dấu gạch, khoảng trắng và xóa.
- Giải mã mã Morse quốc tế cho chữ cái A–Z và chữ số 0–9.
- Tự hoàn tất một ký tự sau khoảng dừng; có thể điều chỉnh thời gian chờ và ngưỡng nhận diện pinch.
- Phát âm báo cho dấu chấm, dấu gạch, thao tác nhập và chuỗi Morse không hợp lệ (nếu thiết bị âm thanh hoạt động).
- Hiển thị bàn phím ảo, ký tự đang nhập và bảng tra mã Morse.
- Tùy chọn ghim cửa sổ lên trên và gửi kết quả vào cửa sổ khác.
- Lưu tùy chọn vào `config.json` trong thư mục dự án.

## Yêu cầu

- Windows và Python 3.12 (phù hợp với phiên bản Python ghi trong `requirements.txt`).
- Webcam.
- Thiết bị âm thanh là tùy chọn; thiếu âm thanh không ngăn việc nhận diện và giải mã trên màn hình.

## Cài đặt và chạy

Mở PowerShell tại thư mục dự án, sau đó chạy:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Cũng có thể khởi chạy bằng module:

```powershell
python -m airmorse
```

Tệp mô hình nhận diện bàn tay được cung cấp tại `models/hand_landmarker.task`. Nếu tệp bị thiếu hoặc nhỏ hơn kích thước tối thiểu, AirMorse sẽ thử tải lại mô hình khi khởi động; khi đó cần kết nối Internet.

## Cách sử dụng

1. Khởi chạy ứng dụng và cho phép ứng dụng truy cập webcam trong cài đặt quyền riêng tư của Windows nếu được yêu cầu.
2. Bật **Ghi nhận chữ** khi bạn muốn nhập. Ứng dụng luôn mở ở trạng thái tắt, nên cử chỉ lúc mới khởi động không thành chữ. Tắt ô này bất cứ lúc nào để dừng ghi; chữ đã giải mã vẫn giữ nguyên, dấu đang nhập dở sẽ bị bỏ. Lựa chọn này không được lưu, nên lần mở sau vẫn bắt đầu ở trạng thái tắt.
3. Đưa bàn tay vào vùng nhìn của webcam. Hình ảnh xem trước được lật ngang để thao tác thuận mắt hơn. Webcam và khung xương bàn tay vẫn chạy khi ghi nhận đang tắt.
4. Chụm đầu ngón tay tương ứng vào ngón cái rồi thả ra để nhập một lệnh:

   | Ngón tay chụm với ngón cái | Lệnh |
   | --- | --- |
   | Ngón trỏ | Dấu chấm (`.`) |
   | Ngón giữa | Dấu gạch (`-`) |
   | Ngón trỏ và ngón giữa cùng lúc | Enter (xuống dòng) |
   | Ngón áp út | Khoảng trắng |
   | Ngón út | Xóa |

5. Ghép các dấu chấm và dấu gạch của một ký tự. AirMorse giải mã sau khi bạn ngừng nhập đủ lâu; mặc định là **0,8 giây** kể từ dấu Morse cuối cùng.
6. Chọn **Gửi phím vào cửa sổ đang chọn** để gửi ký tự đã giải mã vào ứng dụng khác. Sau khi bật, hãy chọn Notepad, trình duyệt hoặc cửa sổ đích trước khi thực hiện thao tác. Trên Windows, AirMorse không gửi phím vào chính cửa sổ AirMorse.

Ví dụ, nhập `...` bằng ba lần chụm ngón trỏ để tạo chữ **S**; đợi ký tự được giải mã rồi nhập `---` bằng ba lần chụm ngón giữa để tạo chữ **O**. Lặp lại `...` để có chuỗi **SOS**.

Lệnh khoảng trắng sẽ kết thúc và giải mã chuỗi đang có trước khi thêm dấu cách. Lệnh Enter làm tương tự rồi xuống dòng. Nếu chuỗi không phải mã Morse hợp lệ, ứng dụng báo lỗi và không thêm dấu cách hay xuống dòng. Lệnh xóa sẽ bỏ dấu chấm/dấu gạch cuối cùng nếu ký tự vẫn đang được nhập; nếu bộ đệm trống, lệnh này xóa ký tự cuối trong phần văn bản đã giải mã.

## Điều chỉnh

- **Ngưỡng chụm**: điều chỉnh độ gần cần thiết giữa ngón cái và đầu ngón tay để nhận diện thao tác chụm. Giá trị lớn hơn dễ kích hoạt hơn; giá trị nhỏ hơn yêu cầu chụm sát hơn. Phạm vi: `0.08–0.40`; mặc định: `0.18`.
- **Thời gian chờ**: thời gian chờ sau dấu chấm/dấu gạch cuối để giải mã ký tự. Phạm vi: `0.5–1.5` giây; mặc định: `0.8` giây.
- **In hoa**: bật để chữ cái mới ra in hoa, tắt để ra in thường. Chữ số không đổi. Chữ đã giải mã trước đó giữ nguyên, nên có thể đổi giữa chừng để trộn hoa và thường. Mặc định là bật.
- **Ghim cửa sổ này lên trên**: giữ cửa sổ AirMorse phía trên các cửa sổ khác.

Các tùy chọn được lưu trong `config.json` ở thư mục gốc dự án. Cấu hình mặc định dùng camera có chỉ số `0`; nếu hệ thống có nhiều camera, có thể đổi trường `camera_index` trong tệp cấu hình trước khi chạy lại ứng dụng.

## Bảng mã Morse

Ứng dụng hỗ trợ chữ cái A–Z và chữ số 0–9. Bảng tra đầy đủ được hiển thị trong cửa sổ AirMorse; dấu câu và các ký tự ngoài bảng chữ cái này chưa được hỗ trợ.

## Chạy kiểm thử

Sau khi cài đặt phụ thuộc, chạy toàn bộ kiểm thử bằng:

```powershell
pytest
```

Các kiểm thử nằm trong `tests/`, bao gồm giải mã Morse, nhận diện pinch, cấu hình, xử lý khung hình, giao diện và gửi phím. Kiểm thử tracker cần MediaPipe và tệp mô hình; nếu thiếu điều kiện này, kiểm thử đó sẽ được bỏ qua.

## Cấu trúc dự án

```text
airmorse/
  gesture/   Nhận diện pinch, máy trạng thái cử chỉ và giải mã Morse
  output/    Âm báo và gửi phím
  ui/        Cửa sổ chính và bàn phím ảo
  vision/    Camera, MediaPipe, xử lý khung hình và lớp phủ bàn tay
models/      Mô hình hand landmarker của MediaPipe
tests/       Kiểm thử tự động
main.py      Điểm khởi chạy
```

## Khắc phục sự cố

- **Không thấy hình ảnh webcam**: kiểm tra kết nối webcam, quyền truy cập camera trong cài đặt quyền riêng tư của Windows, và đóng ứng dụng khác đang chiếm dụng camera. Ứng dụng mặc định mở camera số `0`.
- **Không nhận diện thao tác chụm ổn định**: đưa cả bàn tay vào khung hình, tăng ánh sáng và điều chỉnh **Ngưỡng chụm**. Ngưỡng cao hơn dễ nhận thao tác hơn nhưng cũng có thể làm tăng nhận diện nhầm.
- **Không nghe âm báo**: kiểm tra đầu ra âm thanh. Tính năng âm báo là tùy chọn; văn bản vẫn giải mã trên màn hình khi âm thanh không khả dụng.
- **Không nhập được vào ứng dụng khác**: bật **Gửi phím vào cửa sổ đang chọn**, rồi chuyển sang cửa sổ đích. AirMorse không gửi các dấu Morse đang đệm hoặc chuỗi không hợp lệ; chỉ ký tự đã giải mã, khoảng trắng và thao tác xóa mới được gửi.
- **Không tải/khởi tạo được bộ nhận diện bàn tay**: kiểm tra tệp `models/hand_landmarker.task`; nếu cần tải lại, kết nối Internet và chạy lại ứng dụng.

## Quyền riêng tư

Hình ảnh từ webcam được xử lý cục bộ bởi ứng dụng. Ứng dụng không tải video lên dịch vụ mạng; kết nối Internet chỉ được dùng để tải tệp mô hình nếu mô hình cục bộ bị thiếu hoặc nhỏ hơn kích thước tối thiểu. Tính năng gửi phím chỉ hoạt động khi người dùng bật tùy chọn tương ứng.
