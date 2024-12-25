import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import environ
from celery.app import shared_task

env = environ.Env()


@shared_task(bind=True)
def send_approve_email(self, to_email: str):
    body = f'''
        <html>
          <body>
            <div dir="ltr">
                <p>Hello,</p>
                <p>Thank you for registering with us in "Actogram"!</p>
                <p>Kindly note that your profile has been approved, you can continue your registration through this link</p>
                <a href="{env.str('FE_URL')}">{env.str('FE_URL')}</a>
                <p>Thank you!</p>
                <p>Actogram Team</p>
            </div>
            <div dir="rtl">
                <p>إزيك</p>
                <p>شكراً لطلبك الانضمام لينا في Actogram</p>
                <p>لقد تم الموافقة على طلبك، تقدر دلوقتي تعمل صفحتك الشخصية من الرابط ده</p>
                <a href="{env.str('FE_URL')}">{env.str('FE_URL')}</a>
                <p>شكرا!</p>
                <p>Actogram فريق عمل</p>
            </div>
          </body>
        </html>
        '''
    try:
        send_email(to_email=to_email, body=body, subject='Request to join Actogram has been approved')
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def send_email(to_email: str, subject: str, body: str):
    # Load SMTP configuration from environment variables
    smtp_server = env.str('SMTP_SERVER')
    smtp_port = 587
    smtp_user = env.str('SMTP_USER')
    smtp_password = env.str('SMTP_PASSWORD')
    from_email = env.str('SMTP_USER')
    to_email = to_email

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach the plain text body
    msg.attach(MIMEText(body, 'html'))

    # Send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


# def send_email(play_name: str, to_email: str, qr_path: str):
#     env = environ.Env()
#     smtp_server = env.str('SMTP_SERVER')
#     smtp_port = 587
#     smtp_user = env.str('SMTP_USER')
#     smtp_password = env.str('SMTP_PASSWORD')
#     from_email = env.str('SMTP_USER')
#     to_email = to_email
#     subject = f'QR Code for play: {play_name}'
#     body = f'Please find the QR code attached that redirects to the play: {play_name}.'
#
#     msg = MIMEMultipart()
#     msg['From'] = from_email
#     msg['To'] = to_email
#     msg['Subject'] = subject
#
#     msg.attach(MIMEText(body, 'plain'))
#
#     with open(qr_path, 'rb') as file:
#         part = MIMEApplication(file.read(), Name='qrcode.png')
#         part['Content-Disposition'] = 'attachment; filename="qrcode.png"'
#         msg.attach(part)
#
#     with smtplib.SMTP(smtp_server, smtp_port) as server:
#         server.starttls()
#         server.login(smtp_user, smtp_password)
#         server.send_message(msg)
#
#     print('Email sent successfully!')
