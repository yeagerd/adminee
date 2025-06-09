# Demo Instructions

## Common Setup

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## chat.py

```bash
uvicorn services.chat_service.main:app --port 8000 --host 0.0.0.0 &
python services/demos/chat.py
```
