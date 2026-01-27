import qrcode

ip_address = "http://192.168.3.127:44009"
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(ip_address)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("connect_qr.png")
print(f"QR Code gerado para: {ip_address}")
