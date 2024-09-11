import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def send_email(play_name: str, to_email: str, qr_path: str):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = 'zomor.at.work@gmail.com'  # Replace with your Gmail address
    smtp_password = 'hzyviwiwosbyktrn'  # Replace with your Gmail password or App Password
    from_email = 'zomor.at.work@gmail.com'
    to_email = to_email
    subject = f'QR Code for play: {play_name}'
    body = f'Please find the QR code attached that redirects to the play: {play_name}.'

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    with open(qr_path, 'rb') as file:
        part = MIMEApplication(file.read(), Name='qrcode.png')
        part['Content-Disposition'] = 'attachment; filename="qrcode.png"'
        msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Secure the connection
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

    print('Email sent successfully!')
