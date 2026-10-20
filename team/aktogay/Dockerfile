FROM python:3.12.8-slim-bookworm
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py model.py index.html setup_twins.py ./
COPY static ./static
USER nobody
EXPOSE 8088
CMD ["python", "app.py"]
