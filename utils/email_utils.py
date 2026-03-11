import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import environ
import requests
from celery.app import shared_task

env = environ.Env()


@shared_task(bind=True)
def send_approve_email(self, to_email: str, name: str):
    body = f'''
        <html>
          <body>
            <div dir="ltr">
                <p>Hello, {name}</p>
                <p>Thank you for registering with us in "Actogram"!</p>
                <p>Kindly note that your profile has been approved, you can continue your registration through this link</p>
                <a href="{env.str('FE_URL')}">{env.str('FE_URL')}</a>
                <p>Thank you!</p>
                <p>Actogram Team</p>
            </div>
            <div dir="rtl">
                <p> إزيك يا {name}</p>
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
        send_email_https(
            to_email=to_email,
            body=body,
            subject='Request to join Actogram has been approved',
            name=name,
        )
        return {'status': 'ok', 'email': to_email}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'email': to_email}


@shared_task(bind=True)
def send_hita_arab_ticket_confirmation_email(
    self,
    to_email: str,
    name: str,
    show_name: str,
    reservation_number: str,
    show_date,
    show_time,
    show_venue,
):
    body = f'''
        <html>
          <body>
          <div dir="rtl">
                <p> إزيك يا {name}</p>
                <p>لقد تم حجز التذكرة في عرض ({show_name})</p>
                <p>يوم {show_date} الساعة {show_time} على مسرح {show_venue}</p>
                <p>رقم التذكرة: {reservation_number} </p>
                <p>يتم مراجعة رقم التذكرة والاسم عند الدخول</p>
                <p>شكرا!</p>
                <p>Play-Cast فريق عمل</p>
            </div>
            <div dir="ltr">
                <p>Hello, {name}</p>
                <p>Your reservation has been confirmed for ({show_name})</p>
                <p>On {show_date} at {show_time} at {show_venue}</p>
                <p>Reservation number: {reservation_number}</p>
                <p>Name and reservation number are to be reviewed at the time of entry</p>
                <p>Thank you!</p>
                <p>Play-Cast Team</p>
            </div>
          </body>
        </html>
        '''
    try:
        send_email_https(
            to_email=to_email,
            body=body,
            subject='Request to join Actogram has been approved',
            name=name,
        )
        return {'status': 'ok', 'email': to_email}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'email': to_email}


@shared_task(bind=True)
def send_global_festival_ticket_confirmation_email(
    self,
    to_email: str,
    name: str,
    show_name: str,
    reservation_number: str,
    show_date,
    show_time,
    show_venue,
):
    body = f'''
        <html>
          <body>
          <div dir="ltr">
                <p>Hello, {name}</p>
                <p>Your reservation has been confirmed for ({show_name})</p>
                <p>On {show_date} at {show_time} at {show_venue}</p>
                <p>Reservation number: {reservation_number}</p>
                <p>Name and reservation number are to be reviewed at the time of entry</p>
                <p>Thank you!</p>
                <p>Play-Cast Team</p>
            </div>
            <div dir="rtl">
                <p> إزيك يا {name}</p>
                <p>لقد تم حجز التذكرة في عرض ({show_name})</p>
                <p>يوم {show_date} الساعة {show_time} على مسرح {show_venue}</p>
                <p>رقم التذكرة: {reservation_number} </p>
                <p>يتم مراجعة رقم التذكرة والاسم عند الدخول</p>
                <p>شكرا!</p>
                <p>Play-Cast فريق عمل</p>
            </div>
          </body>
        </html>
        '''
    try:
        send_email_https(
            to_email=to_email,
            body=body,
            subject='Your reservation has been confirmed',
            name=name,
        )
        return {'status': 'ok', 'email': to_email}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'email': to_email}


@shared_task(bind=True)
def send_create_performer_reminder_email(self, to_email: str, name: str):
    body = f'''
        <html>
          <body>
          <div dir="rtl">
                <p> إزيك يا {name}</p>
                <p>بنفكرك إنك لسه معانا في Actogram</p>
                <p>تقدر دلوقتي تعمل صفحتك الشخصية من الرابط ده وتشاركها مع الناس</p>
                <a href="{env.str('FE_URL')}">{env.str('FE_URL')}</a>
                <p>شكرا!</p>
                <p>Actogram فريق عمل</p>
            </div>
            <div dir="ltr">
                <p>Hello, {name}</p>
                <p>This is a reminder that you're still with us in Actogram</p>
                <p>Now, you can create your profile and share it with others via this link</p>
                <a href="{env.str('FE_URL')}">{env.str('FE_URL')}</a>
                <p>Thank you!</p>
                <p>Actogram Team</p>
            </div>            
          </body>
        </html>
        '''
    try:
        send_email_https(
            to_email=to_email,
            body=body,
            subject='Actogram is calling for your artistic profile',
            name=name,
        )
        return {'status': 'ok', 'email': to_email}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'email': to_email}


@shared_task(bind=True)
def send_update_performer_reminder_email(self, to_email: str, name: str):
    body = f'''
        <html>
          <body>
          <div dir="rtl">
                <p> إزيك يا {name}</p>
                <p>بنفكرك إنك لسه معانا في Actogram</p>
                <p>بس للأسف الملف بتاعك نزل للآخر علشان مفيش صورة شخصية ليك على الملف</p>
                <p>مستنيينك ترفع صورتك وتشاركنا بيها علشان تسهل على الناس التواصل وتنتشر أكتر</p>
                <p>ارفع صورك دلوقتي</p>
                <a href="{env.str('FE_URL')}">{env.str('FE_URL')}</a>
                <p>شكرا!</p>
                <p>Actogram فريق عمل</p>
            </div>
            <div dir="ltr">
                <p>Hello, {name}</p>
                <p>This is a reminder that you're still with us in Actogram</p>
                <p>However, your profile has been pushed to the back, because you don't have a profile picture</p>
                <p>We are waiting for you to upload your picture and share with us, to encourage communication.</p>
                <p>Upload your pictures now</p>
                <a href="{env.str('FE_URL')}">{env.str('FE_URL')}</a>
                <p>Thank you!</p>
                <p>Actogram Team</p>
            </div>

          </body>
        </html>
        '''
    try:
        send_email_https(
            to_email=to_email,
            body=body,
            subject='Actogram is calling for your artistic profile',
            name=name,
        )
        return {'status': 'ok', 'email': to_email}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'email': to_email}


def send_email_https(to_email: str, subject: str, body: str, name: str):
    url = env.str('ZEPTO_URL')

    payload = {
        "from": {"address": env.str('PLAY_CAST_EMAIL')},
        "to": [
            {
                "email_address": {
                    "address": to_email,
                    "name": name,
                }
            }
        ],
        "subject": subject,
        "htmlbody": body,
    }
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'authorization': f'Zoho-enczapikey {env.str("ZEPTO_API_KEY")}',
    }

    response = requests.request(
        "POST", url, data=json.dumps(payload, ensure_ascii=False), headers=headers
    )

    print(response.text)


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
