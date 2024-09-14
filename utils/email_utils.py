import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import environ


def send_email(play_name: str, to_email: str, qr_path: str):
    env = environ.Env()
    smtp_server = env.str('SMTP_SERVER')
    smtp_port = 587
    smtp_user = env.str('SMTP_USER')
    smtp_password = env.str('SMTP_PASSWORD')
    from_email = env.str('SMTP_USER')
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
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

    print('Email sent successfully!')
