# 1-Minute Registration Verification Code TTL Enforcement Report

**Date**: 2026-10-29  
**Branch**: `main`  
**Target Environment**: Node.js v24.19.0 / Express / MongoDB / Vite React  

---

## 1. Problem Diagnosis & Root Cause Analysis

### Question 1: How expiry was set and checked before
1. **Setting Expiry**:
   - In [`backend/controllers/authController.js`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/backend/controllers/authController.js), line 137 (`registerUser`) and line 429 (`resendVerification`) were hardcoded to:
     ```javascript
     user.emailVerificationCodeExpiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes
     ```
     This set the TTL to 10 minutes (600,000 ms) instead of 1 minute (60,000 ms).
   - In `verifyEmailCode`, the check was performed as:
     ```javascript
     if (user.emailVerificationCodeExpiresAt && user.emailVerificationCodeExpiresAt.getTime() < Date.now())
     ```
     Because the expiration was set to 10 minutes in the future, codes remained valid for 600 seconds, so any code entered at 35 or 45 seconds was accepted.

2. **Order of Operations & Expiry Invalidation**:
   - When an expired code was rejected in `verifyEmailCode`, neither `emailVerificationCodeHash` nor `emailVerificationCodeExpiresAt` was deleted/cleared in the database document. The expired code remained in storage until overwritten or until verified.

### Question 2: Other routes/places that could let an expired code pass
1. **Legacy Link Route Leak (`/verify-email`)**:
   - In `verifyEmail` (handling both token links and codes):
     ```javascript
     const tokenExpired = user.emailVerificationExpiresAt && user.emailVerificationExpiresAt.getTime() < Date.now();
     const codeExpired = user.emailVerificationCodeExpiresAt && user.emailVerificationCodeExpiresAt.getTime() < Date.now();
     if (tokenExpired && codeExpired) { // BUG: used logical AND
       return res.status(400).json({ code: 'TOKEN_EXPIRED', ... });
     }
     ```
     Because `emailVerificationExpiresAt` (token TTL) was set to 24 hours, `tokenExpired` was `false`. Therefore, `(tokenExpired && codeExpired)` evaluated to `false`, allowing an expired 6-digit code passed to `/verify-email?code=...` to be verified!
   - **Fix**: Separated token match from code match so that `(isTokenMatch && tokenExpired) || (isCodeMatch && codeExpired)` immediately halts verification with `CODE_EXPIRED`.

---

## 2. Changes Implemented

### Single Source of Truth for Registration Code TTL
In [`backend/controllers/authController.js`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/backend/controllers/authController.js):
```javascript
export const VERIFY_CODE_TTL_MS = 60 * 1000; // 1 minute (60 seconds)
```
- Used in `registerUser`:
  ```javascript
  user.emailVerificationCodeExpiresAt = new Date(Date.now() + VERIFY_CODE_TTL_MS);
  ```
  Returns `expiresAt: user.emailVerificationCodeExpiresAt.toISOString()` and `expiresInSeconds: 60`.
- Used in `resendVerification`:
  ```javascript
  user.emailVerificationCodeExpiresAt = new Date(Date.now() + VERIFY_CODE_TTL_MS);
  ```
  Returns `expiresAt: user.emailVerificationCodeExpiresAt.toISOString()` and `expiresInSeconds: 60`.

### Strict Expiry Enforcement in `verifyEmailCode`
1. Checked lockout first (`(user.emailVerificationCodeAttempts || 0) >= 5` -> 400 `TOO_MANY_ATTEMPTS`).
2. Expiry checked FIRST before comparing code hashes:
   ```javascript
   const now = Date.now();
   if (!user.emailVerificationCodeExpiresAt || now > user.emailVerificationCodeExpiresAt.getTime() || !user.emailVerificationCodeHash) {
     user.emailVerificationCodeHash = undefined;
     user.emailVerificationCodeExpiresAt = undefined;
     await user.save();
     return res.status(400).json({
       success: false,
       code: 'CODE_EXPIRED',
       message: 'This code has expired (codes are valid for 1 minute). Please request a new one.',
     });
   }
   ```
   - Stored code is immediately cleared from MongoDB (`undefined`).
   - Does NOT count as a wrong attempt (`emailVerificationCodeAttempts` is not incremented).
   - Responds HTTP 400 `CODE_EXPIRED` with exact required text.

### Immediate Invalidation on Resend
- In `resendVerification`, generating a new code generates a new random 6-digit code, overwriting `emailVerificationCodeHash`, resets attempts to `0`, and assigns a new `emailVerificationCodeExpiresAt` of `Date.now() + 60000`. The old code hash is immediately erased and cannot be used.

### Email Service Text Updates
In [`backend/services/emailService.js`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/backend/services/emailService.js):
- Plaintext: `"This code is valid for 1 minute."`
- HTML: `<div class="expiry">Valid for 1 minute</div>`
- `sendPasswordResetCodeEmail`: Untouched (stays 10 minutes: `"This code will expire in 10 minutes."` / `<div class="expiry">Expires in 10 minutes</div>`).

### Frontend Countdown & Expiry Enforcement
In [`frontend/src/pages/Register.jsx`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/frontend/src/pages/Register.jsx):
- Added text: `"The code is valid for 1 minute"`.
- Live countdown badge: `Expires in 0:45` (turns red when `<= 15s`).
- When countdown reaches 0:
  - Verify button (`#verify-code-btn`) is disabled.
  - Alert shown: `"Code expired - request a new code"`.
  - Resend button enabled as soon as 30s cooldown permits.
  - Resending resets the countdown to 60s and clears expired state.
In [`frontend/src/pages/VerifyEmail.jsx`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/frontend/src/pages/VerifyEmail.jsx):
- Added 1-minute expiration notice and countdown timer.
- Submit button disabled when expired.
In [`frontend/src/pages/Login.jsx`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/frontend/src/pages/Login.jsx):
- Unverified notice clarifies codes are valid for 1 minute.

---

## 3. Files Changed and Scope Confirmation

| File Path | Description of Changes |
|-----------|------------------------|
| [`backend/controllers/authController.js`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/backend/controllers/authController.js) | Defined `VERIFY_CODE_TTL_MS = 60 * 1000`, set 1m in register & resend, check expiry first with code wipe, fixed `/verify-email` leak |
| [`backend/services/emailService.js`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/backend/services/emailService.js) | Updated registration email text and HTML badge to "valid for 1 minute"; kept forgot-password at 10 minutes |
| [`backend/tests/auth.test.js`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/backend/tests/auth.test.js) | Added comprehensive mocked clock tests for 59s pass, 61s rejection, resend invalidation, attempt counting, 10m reset TTL |
| [`frontend/src/pages/Register.jsx`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/frontend/src/pages/Register.jsx) | Subtitle "The code is valid for 1 minute", live countdown, disabled button on expiry, expired alert |
| [`frontend/src/pages/VerifyEmail.jsx`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/frontend/src/pages/VerifyEmail.jsx) | Subtitle and countdown timer for 1 minute code expiry |
| [`frontend/src/pages/Login.jsx`](file:///c:/Users/kavin/Downloads/MockMateAI-fresh/MockMateAI-Clean-Source/frontend/src/pages/Login.jsx) | Alert message mentions 1 minute validity |

**Strict Constraints Confirmation**:
- `backend/.env`: Untouched.
- Forgot-password / reset code: Untouched (10 minutes preserved in `authController.js` and `emailService.js`).
- Login lockout: Untouched (5 attempts / 15 minutes).
- JWT / refresh tokens: Untouched.
- Rate limits: Untouched.
- Resend cooldown: Untouched (30 seconds preserved).
- Interview, scoring, question pool, HR, theory, coding, speech, result, history, ai-service code: Untouched.
- `delete_all_accounts.js`: NOT run.

---

## 4. Test and Build Results

### Backend Automated Test Suite (`npm test`)
- **Baseline**: 123 tests passing.
- **After Changes**: **156 / 156 tests succeeded (0 failures)**.
- Specific TTL Test Suite:
  - `[PASS] Registration response returns expiresInSeconds = 60`
  - `[PASS] Registration response returns expiresAt ISO timestamp`
  - `[PASS] Wrong code at 10s returns HTTP 400`
  - `[PASS] Wrong code at 10s returns INVALID_CODE`
  - `[PASS] Wrong code at 10s counted as 1st attempt (4 remaining)`
  - `[PASS] Correct code accepted at 59 seconds with HTTP 200`
  - `[PASS] Verification returns success: true at 59 seconds`
  - `[PASS] Code at 61 seconds rejected with HTTP 400`
  - `[PASS] Code at 61s returns CODE_EXPIRED`
  - `[PASS] Returns exact expired message for 1 minute code`
  - `[PASS] Expired code hash cleared from database`
  - `[PASS] Resend before 30s returns HTTP 429`
  - `[PASS] Cooldown returns COOLDOWN_ACTIVE`
  - `[PASS] Resend after 30s succeeds with HTTP 200`
  - `[PASS] Resend returns expiresInSeconds = 60`
  - `[PASS] Resend generates a new distinct 6-digit code`
  - `[PASS] Old code rejected after resend`
  - `[PASS] User B resend succeeds with HTTP 200`
  - `[PASS] Old expired code cannot be reused after resend`
  - `[PASS] Fresh code after resend verifies with HTTP 200`
  - `[PASS] 5th attempt returns HTTP 400`
  - `[PASS] 5th attempt returns TOO_MANY_ATTEMPTS`
  - `[PASS] Subsequent attempt on locked code rejected`
  - `[PASS] Locked code returns TOO_MANY_ATTEMPTS`
  - `[PASS] Forgot password returns HTTP 200`
  - `[PASS] Forgot-password code is still valid after 9 minutes (10min TTL)`
  - `[PASS] Single-use reset token issued at 9 minutes`

### Frontend Build (`npm run build`)
```
> vite build
✓ 1282 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.76 kB │ gzip:  0.43 kB
dist/assets/index-da1bbffa.css   33.07 kB │ gzip:  6.81 kB
dist/assets/index-43402ecf.js   329.74 kB │ gzip: 92.74 kB
✓ built in 2.03s
```
Zero build errors.

---

## 5. Live Check Execution

- **Target Alias**: `divyae.ramachandran+mm5@gmail.com`
- **Password**: `Test1234x`
- **Registration Call**: `POST http://localhost:5000/api/auth/register`
- **Registration Response**:
  ```json
  {
    "success": true,
    "requiresVerification": true,
    "emailSent": true,
    "expiresAt": "2026-10-29T13:58:52.961Z",
    "expiresInSeconds": 60,
    "message": "Registration successful! A 6-digit verification code has been sent to your email address.",
    "email": "divyae.ramachandran+mm5@gmail.com"
  }
  ```
- **Backend Server Log**:
  ```
  [EmailService] Email dispatched successfully to divyae.ramachandran+mm5@gmail.com (MessageID: <c02fe589-b396-6117-25c6-59367b69d971@gmail.com>)
  ```
- **Live User Verification Tests**:
  - **Test 1 (Within 1 Minute)**: User enters the 6-digit code received within 60 seconds. [Awaiting user report]
  - **Test 2 (After > 1 Minute)**: User requests a new code or enters code after 60 seconds. [Awaiting user report]

### 6. Account Cleanup Action
- Per user request, scanned all databases for unverified accounts and `dr586221@gmail.com`.
- Purged unverified test record `divyae.ramachandran+mm5@gmail.com` (1 document removed, cascaded records checked).
- Confirmed zero documents exist for `dr586221@gmail.com` across all collections and databases.
- The email address `dr586221@gmail.com` is completely unblocked and ready for new account creation.

