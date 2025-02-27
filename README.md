# Auto chatvn

Tự động trả lời tin nhắn chatvn

## Cách sử dụng

1. Truy cập `https://cvnl.app` trên trình duyệt Chrome và đăng nhập tài khoản.
2. Nhấn `F12` để mở console, paste code này để lấy `TOKEN`:
```js
console.log(localStorage.getItem("token"));
```
3. Lấy Gemini API Key tại [đây](https://aistudio.google.com/app/apikey)
4. Mở `cmd` tại thư mục của repo, gõ lệnh sau để chạy `autochatvn`:
```bash
set GENKEY=<GEMINI_API_KEY>
set TOKEN=<TOKEN>
python autochatvn.py
```
