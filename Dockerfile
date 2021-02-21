FROM python:3

LABEL org.opencontainers.image.source https://github.com/dries007/JenkinsViewer

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY . .

CMD [ "gunicorn", "app:app" ]
