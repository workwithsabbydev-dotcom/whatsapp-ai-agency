# WhatsApp AI Agency Platform 🚀

A production-ready, multi-tenant AI automation backend built for WhatsApp. This platform allows an agency to host multiple businesses (tenants) from a single unified server, connecting WhatsApp to Google Gemini and Google Sheets for highly customized, intelligent customer interactions.

---

## 1. Overview

This platform acts as a high-speed, asynchronous middleman. When a customer messages one of your client's WhatsApp numbers, the system:
1. **Identifies the Business**: Routes the webhook via the Meta `phone_number_id`.
2. **Loads Memory**: Pulls the last 10 messages from the Neon PostgreSQL database.
3. **Retrieves Knowledge**: Pulls live FAQs and inventory from that business's Google Sheet (cached for speed in the background).
4. **Generates Response**: Passes the context securely to Gemini (using low temperature for hallucination prevention).
5. **Replies**: Sends the AI response back to the customer via the WhatsApp Cloud API.
6. **Human Handoff**: If the user asks for a human, it automatically pauses the AI and notifies the business.

---

## 2. Architecture

- **Backend**: Python 3.10+, FastAPI (Asynchronous)
- **Database**: Neon Serverless PostgreSQL
- **ORM**: SQLAlchemy 2.0 (Asyncpg) + Alembic for migrations
- **AI Engine**: Google Gemini API (1.5 Flash/Pro) via Async HTTPX
- **Data Source**: Google Sheets API (w/ TTLCache background refresh)
- **Messaging**: Meta WhatsApp Cloud API (v18.0)

---

## 3. Setup Steps

1. **Clone the repository** and navigate to the root directory.
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Setup Database**: Ensure you have a Neon PostgreSQL database URL.
5. **Run Migrations** to create the tables:
   ```bash
   alembic upgrade head
   ```

---

## 4. Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
PORT=8000
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://<neon_user>:<neon_pass>@<neon_host>/neondb
GEMINI_API_KEY=your_google_ai_studio_master_key
GOOGLE_CREDENTIALS_JSON=path/to/service-account.json # Or raw JSON string for Render
WEBHOOK_VERIFY_TOKEN=your_secure_random_string # Used in Meta Dev Portal
ADMIN_API_KEY=your_secure_random_string # For future admin routes
ENCRYPTION_KEY=your_fernet_key # For future token encryption
```

---

## 5. Google Setup (Sheets + Service Account)

To allow the AI to read dynamic business data (FAQs, inventory):
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Sheets API**.
3. Go to **IAM & Admin > Service Accounts** and create a new Service Account.
4. Generate a new JSON Key for this account and save it.
5. In your `config.py` / `.env`, point `GOOGLE_CREDENTIALS_JSON` to this file path.
6. **Important**: Open the target Google Sheet and *Share* it (Viewer access) with the Service Account email address.

---

## 6. Gemini Setup

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Generate an API Key.
3. Paste this key into `GEMINI_API_KEY` in your `.env`.
> Note: Your agency uses one "Master Key" to power all tenant conversations to centralize billing.

---

## 7. WhatsApp Cloud API Setup

1. Go to the [Meta Developer Dashboard](https://developers.facebook.com/).
2. Create an App (Type: Business).
3. Add the **WhatsApp** product.
4. In the **Configuration** tab, set up your Webhook:
   - **Callback URL**: `https://your-domain.com/webhook` (Use ngrok for local dev).
   - **Verify Token**: Must exactly match your `WEBHOOK_VERIFY_TOKEN` in `.env`.
   - Subscribe to the `messages` field.
5. Note down the **Phone Number ID** and generate a **Permanent Access Token** in the System Users tab.

---

## 8. Local Run Guide

1. **Start the FastAPI Server**:
   ```bash
   uvicorn app.main:app --reload
   ```
2. **Expose to the Web** (so Meta can reach your localhost):
   ```bash
   ngrok http 8000
   ```
3. Copy the `https://...ngrok-free.app` URL and paste it into your Meta Webhook configuration as `https://...ngrok-free.app/webhook`.

---

## 9. Deployment on Render

1. Create a new **Web Service** on [Render](https://render.com/).
2. Connect your GitHub repository.
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Go to the **Environment** tab and paste all variables from your `.env`. 
   > *Tip: For `GOOGLE_CREDENTIALS_JSON`, you can paste the literal minified JSON string directly into the Render secret field so you don't have to commit a file.*
6. Deploy and update your Meta Webhook URL to the new `onrender.com` domain.

---

## 10. Adding a New Business Guide

To onboard a new agency client:
1. Connect to your Neon PostgreSQL database (via TablePlus, pgAdmin, or DBeaver).
2. Insert a new row into the `businesses` table:
   - `name`: "Client Company Name"
   - `wa_phone_number_id`: The Meta Phone ID for this specific client.
   - `wa_access_token`: The Meta Access token for this specific client.
   - `sheets_id`: The ID of their Google Sheet (found in the URL `docs.google.com/spreadsheets/d/{sheets_id}/edit`).
   - `system_prompt`: "You are an assistant for Client Company. Always be polite..."
3. The system will automatically route messages to this client based on the `phone_number_id` hitting the webhook!

---

## 11. Troubleshooting

- **Webhook Validation Fails**: Ensure `hub.verify_token` matches your `.env` perfectly. Check your FastAPI logs for 403 errors.
- **AI Hallucinations**: Add stricter rules to the business's `system_prompt` in the database, and ensure their Google Sheet is populated correctly.
- **Messages Repeated**: The system uses a `TTLCache` to prevent duplicates. Ensure you are returning `{"status": "ok"}` to Meta immediately (which the background tasks orchestration inherently handles).
- **Service Account Errors**: Ensure the Google Sheet is shared with the *exact* email address generated in the Google Cloud Service Account.
