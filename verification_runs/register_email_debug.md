# Registration & Email Verification Diagnostic Report

**Timestamp**: 2026-10-29T17:31:00+05:30  
**Environment**: Windows, Node.js v24.19.0, Vite Dev Server, Nodemon Express Backend  

---

## Part 1: Which Code is Actually Running

1. **Port & Process Ownership**:
   - **Port 5000 (Backend API)**:
     - **Process**: `node.exe` (PID: 26976)
     - **Command Line**: `"C:\Program Files\nodejs\node.exe" server.js`
     - **Parent Process**: `nodemon.js` (PID: 12204)
     - **Folder**: `C:\Users\kavin\Downloads\MockMateAI-fresh\MockMateAI-Clean-Source\backend`
   - **Port 3000 (Frontend)**:
     - **Process**: `node.exe` (PID: 24256)
     - **Command Line**: `"node" "C:\Users\kavin\Downloads\MockMateAI-fresh\MockMateAI-Clean-Source\frontend\node_modules\vite\bin\vite.js"`
     - **Folder**: `C:\Users\kavin\Downloads\MockMateAI-fresh\MockMateAI-Clean-Source\frontend`
   - **Verification**: Both running processes are running live directly out of `MockMateAI-fresh\MockMateAI-Clean-Source` (not older builds, not static dist, not cache).

2. **Source of 6-Digit Code Screen**:
   - **File**: `frontend/src/pages/Register.jsx`
   - **Trigger Condition**: When `registeredEmail` was truthy (set upon receiving `{ success: true }` from `POST /api/auth/register`).
   - **Issue Found**: The screen displayed *"We sent a 6-digit verification code to your email"* unconditionally, even when the server returned `emailSent: false`.
   - **Flow Decision**: Kept the **LINK flow (preferred, least change)**. The post-register screen now displays **"Check Your Inbox"**, instructs the student to check their inbox and click the verification link, provides a Resend button with a 30s cooldown timer, and never displays 6 code boxes or claims an email was sent if `emailSent` is false.

---

## Part 2: Flow Alignment

- **Chosen Flow**: **LINK verification flow**
- **Post-Registration Screen**:
  - If `emailSent: true`: Displays *"We sent a verification link to your email address: [email]. Please check your inbox (and spam folder) and click the link to activate your account."*
  - If `emailSent: false`: Displays an alert indicating mail delivery could not be completed and invites resending once SMTP is configured. Never claims *"We sent"*.
- **Verification Page (`VerifyEmail.jsx`)**: Automatically verifies incoming link tokens (`/verify-email?token=...&email=...`) and redirects to login with success state.

---

## Part 3: SMTP & Email Delivery Diagnostics

### 1. SMTP Environment Presence Table
| Variable | Present | Placeholder Check | Notes |
| :--- | :--- | :--- | :--- |
| `SMTP_HOST` | **true** | No | Currently `smtp.ethereal.email` (Ethereal test sandbox) |
| `SMTP_PORT` | **true** | No | 587 |
| `SMTP_SECURE`| **true** | No | false |
| `SMTP_USER` | **true** | No | Non-placeholder account |
| `SMTP_PASS` | **true** | No | Non-placeholder secret |
| `MAIL_FROM` | **true** | No | Matches `SMTP_USER` |
| `CLIENT_URL` | **true** | No | `http://localhost:3000` |
| `MAIL_FROM matches SMTP_USER` | **yes** | - | Consistent sender address |

### 2. Backend Restart & Health
- Restarted backend checked on port 5000: **HTTP 401** on `/api/auth/me` (healthy unauthenticated check).

### 3. Test Email Execution (`npm run test-email`)
- **Recipient**: `divyae.ramachandran@gmail.com`
- **Output Line**:
  ```
  [EmailService] Email dispatched successfully to divyae.ramachandran@gmail.com (MessageID: <11d753a6-a64a-ab98-4d2f-f96344de256a@ethereal.email>)
  [SUCCESS] Test email dispatched successfully.
  ```

### 4. Registration API Live Test
- **POST `/api/auth/register` (alias: `divyae.ramachandran+mm2@gmail.com`)**:
  - **HTTP Status**: `201 Created`
  - **emailSent**: `true`
  - **Backend Console Log**:
    ```
    [EmailService] Email dispatched successfully to divyae.ramachandran+mm2@gmail.com (MessageID: <4d7902ac-8cb7-cc98-f583-4b24bddacf4f@ethereal.email>)
    ```

### 5. Why Real Emails Do Not Arrive in Gmail Inbox
- **Root Cause**: The current `SMTP_HOST` in `backend/.env` is `smtp.ethereal.email`.
- **Mapping**: Ethereal Mail is an isolated developer simulation server. It returns HTTP 250 Accepted and generates a web preview URL, but **does not relay or deliver outgoing messages across the public Internet to Google Mail / Gmail MX servers**.

---

## Part 4: Test Counts & Build Verification

- **Backend `npm test` Baseline**: 87 / 87 PASSED (0 failures)
- **Backend `npm test` After Fixes**: **87 / 87 PASSED (0 failures)**
- **Frontend `npm run build`**: **SUCCESS (0 errors)** in 2.29s

---

## Files Changed

1. `frontend/src/pages/Register.jsx` (Converted post-register screen to LINK flow; removed 6-digit input boxes and unused code states; added condition guarding against false "We sent" messages).
2. `frontend/src/pages/VerifyEmail.jsx` (Aligned token verification link flow).
3. `backend/services/emailService.js` (Unified verification email template to send the verification link).

No other files (interview, scoring, question pool, HR, theory, coding, speech, result, history, ai-service) were touched.

---

## The One Thing You Must Do

To receive real emails in your personal inbox (`divyae.ramachandran@gmail.com`):
In `backend/.env`, replace the Ethereal host with Gmail SMTP and a 16-character **Google App Password**:
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your_gmail@gmail.com
SMTP_PASS=your_16_character_app_password
MAIL_FROM="AI Interview Assistant" <your_gmail@gmail.com>
```
*(Standard Google account passwords are blocked by Google for SMTP; generate a 16-character code in Google Account > Security > 2-Step Verification > App Passwords).*
