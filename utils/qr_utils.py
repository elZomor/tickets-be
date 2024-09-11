import qrcode

def generate_qr(url: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill='orange', back_color='white')

    img_path = 'qrcode.png'
    img.save(img_path)
    return img_path