FROM python:3.7.7-alpine AS deps

RUN apk add --no-cache libffi-dev gcc musl-dev make

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt --no-warn-script-location

FROM python:3.7.7-alpine
WORKDIR /app
COPY --from=deps /root/.local /root/.local
COPY . .
RUN chmod +x /app/export.sh /app/start.sh
RUN ln -s /app/export.sh /bin
RUN ln -s /app/start.sh /bin
ENV LIGHTMILL_DB_URI /data/experiments.db
ENV LIGHTMILL_EXPORT_DIR /data/export
ENV LIGHTMILL_PORT 80
VOLUME [ "/data" ]
EXPOSE 80
CMD ["python", "-uO", "start.py"]
