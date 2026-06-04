FROM python:3.9-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# Hugging Face က Port 7860 ကို သုံးတာမို့ ခွင့်ပြုပေးခြင်း
EXPOSE 7860

CMD ["python", "app.py"]
