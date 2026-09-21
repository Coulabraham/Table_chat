FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system tablechat && adduser --system --ingroup tablechat tablechat
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -c constraints.txt -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput --settings=tablechat.settings.development && chown -R tablechat:tablechat /app
USER tablechat
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "tablechat.asgi:application"]
