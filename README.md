# WhatsApp Voice + OpenAI Realtime Integration

This project is a **Python service** that integrates **WhatsApp Voice Calls** with the **OpenAI Realtime API**.  
When a user initiates a WhatsApp voice call, the server instantly answers, establishes a media session (mocked locally), and connects the call to OpenAI Realtime.  

The AI assistant:
1. Greets the user with: **"It's time to take your medicine"**  
2. Listens to user speech in real time  
3. Responds based on a provided medicine context (default: **paracetamol**)  

> ⚠️ Note: This implementation uses a **mock WebRTC adapter** for local development and testing. In production, replace it with a real adapter that handles SDP/ICE/DTLS/RTP according to WhatsApp media specs.

---

## Features

- Handles **WhatsApp voice call webhooks**
- Picks up calls automatically
- Connects call audio to **OpenAI Realtime API**
- AI speaks first, then converses based on medicine JSON
- Async, type-hinted Python code
- Mocked WebRTC adapter for dev/testing
- **Dockerfile** + **docker-compose** for local deployment
- **Pytest** unit tests
- **GitHub Actions CI** workflow (lint, test, docker build)

---

## Project Structure

```
.
├─ .github/workflows/ci.yml        # CI pipeline
├─ docker-compose.yml
├─ Dockerfile
├─ .env.example
├─ README.md
├─ requirements.txt
├─ app/
│  ├─ main.py                      # Entrypoint (HTTP server)
│  ├─ config.py                    # Loads environment variables
│  ├─ webhook\_handler.py           # Handles WhatsApp webhook events
│  ├─ whatsapp\_client.py           # Calls WhatsApp API endpoints
│  ├─ openai\_realtime.py           # Wrapper for OpenAI Realtime
│  ├─ webrtc\_adapter.py            # Mock adapter (replace in prod)
│  ├─ medicine\_context.py          # Static medicine JSON
│  ├─ call\_session.py              # Orchestrates call lifecycle
│  ├─ utils.py                     # Logging, helpers
│  └─ tests/                       # Pytest suite

```

---

## Requirements

- Docker & docker-compose
- A WhatsApp Business API account (you are a tech provider)
- OpenAI API key with Realtime API access

---

## Setup

1. **Clone this repo**
   ```bash
   git clone https://github.com/your-org/whatsapp-openai-realtime.git
   cd whatsapp-openai-realtime
   ```

2. **Create `.env` from template**

   ```bash
   cp .env.example .env
   ```

3. **Fill in your credentials** in `.env`:

   ```env
   WHATSAPP_API_BASE_URL=https://graph.facebook.com/v23
   WHATSAPP_TOKEN=your_whatsapp_token_here
   WHATSAPP_WEBHOOK_SECRET=verify_token_or_hmac_secret
   OPENAI_API_KEY=sk-xxxx
   SERVICE_PORT=8080
   LOG_LEVEL=INFO
   CALL_TIMEOUT_SECONDS=300
   ```

4. **Build & run**

   ```bash
   docker-compose up --build
   ```

---

## Endpoints

* `GET /health` → health check (`200 OK`)
* `POST /webhook` → WhatsApp webhook receiver

  * Call initiation events trigger AI call flow
  * Other events are logged & acknowledged

---

## Testing Locally

### Run unit tests

```bash
docker-compose run --rm app pytest
```

### Simulate a WhatsApp webhook

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer verify_token_or_hmac_secret" \
  -d '{
        "object": "whatsapp_business_account",
        "entry": [{
          "changes": [{
            "value": {
              "call_id": "test-call-123",
              "sdp": "dummy-offer-sdp",
              "event": "call.initiated"
            }
          }]
        }]
      }'
```

Expected log output:

```
[INFO] Incoming call webhook received
[INFO] Call ID: test-call-123
[INFO] Created SDP answer
[INFO] Sent call answer to WhatsApp API
[INFO] Connected to OpenAI Realtime
[INFO] AI: "It's time to take your medicine"
```

---

## Medicine Context

The AI uses the following static JSON to answer medication questions:

```json
{
  "name": "paracetamol",
  "form": "tablet",
  "route": "oral",
  "meal_configuration": "after meal",
  "time": "08:00",
  "dosage_value": 500,
  "dosage_unit": "mg"
}
```

In production, you can replace this with dynamic data (e.g. from your hospital system).

---

## Production Notes

* Replace `webrtc_adapter.py` mock with a real implementation (e.g. server-side WebRTC stack or WhatsApp Media Gateway).
* Secure webhook endpoint with proper signature validation (X-Hub-Signature).
* Rotate secrets regularly.
* Monitor logs for dropped calls or API errors.

---

## Development Roadmap

* ✅ User-initiated call flow
* 🔜 Business-initiated call flow (for scheduled reminders)
* 🔜 Real WebRTC adapter integration
* 🔜 Persistent patient medicine schedules

---

## License

MIT