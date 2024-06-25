import os
from datetime import datetime
from celery import Celery
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from sqlalchemy.orm import Session
from fastapi import Depends
from models import Container, User
from async_db import get_db
from dotenv import load_dotenv

load_dotenv()

# Set up the results directory
RESULTS_DIR = os.path.join('static', 'containers', 'static', 'containers', '{container_id}')

# Load environment variables for email configuration
class EmailConfig:
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_FROM = os.getenv('MAIL_FROM')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_FROM_NAME = os.getenv('MAIL_FROM_NAME')

# Set up the FastAPI Mail connection configuration
email_conf = ConnectionConfig(
    MAIL_USERNAME=EmailConfig.MAIL_USERNAME,
    MAIL_PASSWORD=EmailConfig.MAIL_PASSWORD,
    MAIL_FROM=EmailConfig.MAIL_FROM,
    MAIL_PORT=EmailConfig.MAIL_PORT,
    MAIL_SERVER=EmailConfig.MAIL_SERVER,
    MAIL_FROM_NAME=EmailConfig.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
)

# Set up the Celery application
celery_app = Celery('create_task', broker='amqp://guest:guest@localhost:5672//')

@celery_app.task
async def send_analysis_results(container_id: int):
    """
    Отправляет результаты анализа пользователю, связанному с контейнером.
    """
    results_dir = RESULTS_DIR.format(container_id=container_id)
    if os.path.exists(results_dir):
        email_body = ''
        for filename in os.listdir(results_dir):
            if filename.endswith('.txt'):
                results_file = os.path.join(results_dir, filename)
                if os.path.getsize(results_file) > 0:
                    with open(results_file, 'r') as file:
                        email_body += ''.join([line.strip() for line in file]) + '\n'
        if email_body.strip():
            async with Session(get_db()) as db:
                container = await db.get(Container, container_id)
                if container:
                    user = container.user
                    message = MessageSchema(
                        subject="Результаты анализа",
                        recipients=[user.email],
                        body=email_body,
                        subtype="plain"
                    )
                    await FastMail(email_conf).send_message(message)
                    print(f"Отправлены результаты для контейнера {container_id} в {datetime.now()}")
                else:
                    print(f"Пропущен контейнер {container_id} в {datetime.now()} (контейнер не найден)")
    else:
        print(f"Пропущен контейнер {container_id} в {datetime.now()} (нет директории с результатами)")

@celery_app.task
async def send_results(container_id: int, db: Session = Depends(get_db)):
    """
    Отправляет результаты анализа для указанного ID контейнера.
    """
    try:
        container = await db.get(Container, container_id)
        if container:
            await send_analysis_results.delay(container_id)
            return {"message": "Результаты анализа отправлены пользователю."}
        else:
            return {"error": "Контейнер не найден."}
    except Exception as e:
        return {"error": f"Возникла ошибка: {str(e)}"}

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Настраивает периодическую задачу для отправки результатов анализа.
    """
    sender.conf.beat_schedule = {
        'send_analysis_results': {
            'task': 'send_analysis_results',
            'schedule': 30.0,  # 5 минут
        },
    }

if __name__ == '__main__':
    celery_app.start()
    celery_app.tasks.register(send_analysis_results)

