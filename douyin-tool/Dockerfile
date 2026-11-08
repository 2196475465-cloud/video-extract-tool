FROM python:3.11-slim

# Chrome + 中文字体（中文字体缺失会影响抖音页面渲染）
RUN apt-get update \
 && apt-get install -y --no-install-recommends wget gnupg ca-certificates fonts-wqy-zenhei \
 && wget -qO- https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
 && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends google-chrome-stable \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server/ /app/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-u", "app.py"]
