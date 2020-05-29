FROM python:3.7

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .
RUN chmod +x /app/export.sh /app/start.sh
RUN ln -s /app/export.sh /bin
RUN ln -s /app/start.sh /bin
ENV LIGHTMILL_DB_URI /data/experiments.db
ENV LIGHTMILL_EXPORT_DIR /data/export
ENV LIGHTMILL_PORT 80
VOLUME [ "/data" ]
EXPOSE 80
CMD [ "./start.sh" ]