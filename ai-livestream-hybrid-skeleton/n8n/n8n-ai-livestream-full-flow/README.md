# n8n AI Livestream Full LLM Flow

Workflow này thêm bước LLM giữa Normalize và Python /speak.

## Flow

```text
Webhook - Incoming Comment
  ↓
Normalize + Basic Filter
  ↓
Skip?
  ├─ true  → Respond Skipped
  └─ false → LLM - Azure OpenAI JSON
              ↓
            Parse LLM JSON Safe
              ↓
            HTTP - Python /speak
              ↓
            Respond OK
```

## Required n8n environment variables

Set trong environment của n8n:

```bash
AZURE_OPENAI_ENDPOINT=https://YOUR_RESOURCE_NAME.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=YOUR_DEPLOYMENT_NAME
AZURE_OPENAI_API_KEY=YOUR_KEY
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AI_LIVESTREAM_PYTHON_URL=http://127.0.0.1:8088/speak
```

Nếu n8n chạy bằng Docker còn Python chạy trên Windows host, `127.0.0.1` trong Docker là container, không phải máy host. Dùng:

```bash
AI_LIVESTREAM_PYTHON_URL=http://host.docker.internal:8088/speak
```

## Test payload

POST vào webhook:

```json
{
  "comment": "shop ơi giá bao nhiêu?",
  "user": "viewer_001"
}
```

## Ghi chú

- Workflow dùng HTTP Request node để gọi Azure OpenAI, tránh phụ thuộc version node OpenAI của n8n.
- Node `Parse LLM JSON Safe` xử lý markdown fenced JSON, double-encoded JSON, missing fields, invalid emotion/action và fallback.
