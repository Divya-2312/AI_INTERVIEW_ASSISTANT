# AI Interview Assistant - Operational & Authentication Guide

This guide details how to configure, run, and verify the upgraded AI Interview Assistant authentication system and full-stack application.

---

## 1. Upgraded Authentication Architecture

The authentication layer has been enhanced with enterprise-grade security:
1. **Email Verification Link on Sign Up**:
   - New user accounts are created with `emailVerified = false`.
   - A cryptographically random 32-byte token is hashed using SHA-256 and stored with a 24-hour expiration.
   - The user receives an activation link: `http://localhost:3000/verify-email?token=<token>&email=<email>`.
   - Logging in prior to email verification returns `403 EMAIL_NOT_VERIFIED` with a 30-second cooldown resend action.
   - Existing legacy users without the `emailVerified` field are backward-compatible and log in without friction.

2. **JWT Authentication & Refresh Token Rotation**:
   - **Access Token**: Short-lived (15 minutes), payload `{ id }`, signed with `JWT_SECRET`. Stored in memory on the client.
   - **Refresh Token**: 7-day token (30 days if "Remember me" is checked), signed/generated as an opaque random token. Stored as an `httpOnly`, `SameSite=Lax` cookie.
   - **Rotation**: Every call to `POST /api/auth/refresh` issues a new access token and rotates the refresh token. Old tokens are invalidated; replay attempts trigger session revocation.
   - **Silent Refresh Interceptor**: When access tokens expire, the frontend Axios/Fetch interceptor catches `401 TOKEN_EXPIRED`, silently refreshes the session, and seamlessly retries the request without interrupting the user.

3. **Forgot Password via Emailed 6-Digit Code**:
   - `POST /api/auth/forgot-password` returns a uniform generic success response to avoid email enumeration.
   - Generates a secure 6-digit numeric verification code using `crypto.randomInt` (10-minute expiry, max 5 attempts).
   - `POST /api/auth/verify-reset-code` validates the code and returns a short-lived single-use `resetToken`.
   - `POST /api/auth/reset-password` updates the password, invalidates all existing refresh sessions, and sends a security confirmation notification email.

4. **Account Lockout & Rate Limiting**:
   - 5 consecutive failed login attempts locks the account for 15 minutes (`423 ACCOUNT_LOCKED`).
   - `express-rate-limit` enforces strict IP-level rate limiting on sensitive auth routes (15 requests per 15 minutes).
   - HTTP security headers provided by `helmet`.

---

## 2. Environment Variables (.env)

Add the following variables to your `mockmate/backend/.env`:

```env
PORT=5000
MONGODB_URI=mongodb://localhost:27017/ai_interview_assistant
CLIENT_URL=http://localhost:3000
AI_SERVICE_URL=http://localhost:8000/api/ai

# JWT Secrets
JWT_SECRET=your_jwt_access_secret_key_here
JWT_REFRESH_SECRET=your_jwt_refresh_secret_key_here

# SMTP Email Configuration (Optional in Dev Mode)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_specific_password_here
MAIL_FROM="AI Interview Assistant" <no-reply@ai-interview-assistant.com>
```

### Dev Mode Fallback (Zero Config Needed)
If `SMTP_HOST`, `SMTP_USER`, or `SMTP_PASS` are unconfigured or contain placeholders, the backend runs in **DEV MODE**:
- Emails are not sent over the wire.
- The verification link or 6-digit code is printed directly to the backend terminal in a prominent banner.
- The application flow can be tested locally without third-party email setup.

---

## 3. How to Obtain an SMTP App Password (Gmail)

To dispatch real emails through Gmail SMTP:
1. Go to your **Google Account** settings: [https://myaccount.google.com/](https://myaccount.google.com/).
2. Select **Security** from the left navigation.
3. Under "How you sign in to Google", ensure **2-Step Verification** is turned **ON**.
4. In the search bar at the top, search for **App passwords** (or go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)).
5. Under "App name", enter `AI Interview Assistant` and click **Create**.
6. Google will generate a **16-character passcode** (e.g., `abcd efgh ijkl mnop`).
7. Copy the passcode and paste it into `SMTP_PASS` in your `mockmate/backend/.env` without spaces.
8. Set `SMTP_USER=your_gmail_address@gmail.com`.
9. Verify the connection by running:
   ```bash
   cd mockmate/backend
   npm run test-email your_personal_email@gmail.com
   ```

---

## 4. Starting the Application

### 1. MongoDB & Ollama
Ensure local services are running:
- MongoDB on `localhost:27017`
- Ollama on `localhost:11434` with model `llama3.2:3b` (or fine-tuned model `mockmate-llama-ft`)

### 2. AI Engine Service (FastAPI)
```powershell
cd ai-service
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Health verification: `curl http://localhost:8000/health`

### 3. Backend REST API (Node/Express)
```powershell
cd backend
npm run dev
```
Health verification: `curl http://localhost:5000/api/health`

### 4. Frontend Application (React + Vite)
```powershell
cd frontend
npm run dev
```
Open in browser: `http://localhost:3000`

---

## 5. Automated Tests

### Backend Authentication Tests (40 Assertions)
```powershell
cd backend
npm test
```
Covers registration, email verification, login, JWT rotation, lockout, forgot password code validation, password reset, and legacy user compatibility.

### AI Service Tests (45 Tests)
```powershell
cd ai-service
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Frontend Build
```powershell
cd frontend
npm run build
```
