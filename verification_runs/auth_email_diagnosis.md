# Diagnostic Report: Auth Registration, Email Verification & Login

**Date:** 2026-10-29  
**System:** MockMate AI Clean Source Backend & Frontend  

---

## 1. Executive Summary & Root Cause

The investigation into why verification emails were not received revealed four distinct factors across the stack:

1. **SMTP Configuration Status: NOT CONFIGURED (MISSING)**:
   - `SMTP_HOST`: `false` (missing)
   - `SMTP_PORT`: `false` (missing)
   - `SMTP_USER`: `false` (missing)
   - `SMTP_PASS`: `false` (missing)
   - `MAIL_FROM`: `false` (missing)
   - `CLIENT_URL`: `true` (`http://localhost:3000`)
   - Placeholder check: Neither `SMTP_USER` nor `SMTP_PASS` contain placeholder strings because both environment variables are completely unset in `backend/.env`.
   - Running `npm run test-email` directly confirmed:
     ```text
     --- AI Interview Assistant SMTP Test Utility ---
     Checking SMTP Configuration: NOT CONFIGURED (DEV FALLBACK)
     Target Recipient: student.test@example.com
     [EmailService] Cannot send email to student.test@example.com: SMTP is not configured on this server. Configure SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASS in backend/.env to send real emails.
     [FAILED] Failed to dispatch test email: SMTP server is not configured on this system. Verification email could not be dispatched.
     ```

2. **Root Cause Category**:
   - **Primary Cause:** **SMTP missing from `.env`**.
   - **Secondary Contributing Cause:** **Success message hiding the failure in the original code**. Previously, `emailService.js` fell back to returning `{ success: true, devMode: true }` when unconfigured. `authController.js` previously ignored the return value and returned a generic success message, and the frontend registration page unconditionally told the student *"We have sent a verification link to your email address"*, completely hiding the fact that no email could be dispatched.

3. **Front-End Route & Port Verification**:
   - `CLIENT_URL` resolves to `http://localhost:3000`.
   - The Vite frontend server runs on port `3000`.
   - The React router route is declared in `frontend/src/App.jsx`:
     `<Route path="/verify-email" element={<VerifyEmail />} />`
   - The constructed verification link is:
     `${CLIENT_URL}/verify-email?token=${encodeURIComponent(verificationToken)}&email=${encodeURIComponent(email)}`
   - **Verification:** The link format (`http://localhost:3000/verify-email?token=...&email=...`) matches the real client port and route structure.

---

## 2. Current End-to-End Workflow Analysis

### A. Registration (`POST /api/auth/register`)
- **Inputs:** `name`, `email`, `password`, `degree`, `university`, `targetRole`.
- **Validation:** Enforces non-empty name and email, valid email regex format, and password security rules (minimum 8 characters, at least 1 letter and 1 number).
- **Duplicate Prevention:** Checks `User.findOne({ email: normalizedEmail })`. Returns HTTP 409 `EMAIL_ALREADY_EXISTS` if already present.
- **Token Generation:** Generates a secure 32-byte cryptographic random hex token (`verificationToken`). Hashes it with SHA-256 for database storage (`emailVerificationTokenHash`).
- **User Record Creation:** Saves document with `emailVerified: false`, `emailVerificationExpiresAt: Date.now() + 24 hours`, and `lastEmailVerificationSentAt: Date.now()`.
- **Email Dispatch:**
  - Calls `await emailService.sendVerificationEmail(user.email, user.name, verificationToken)`.
  - Checks `isSmtpConfigured()`. Since SMTP is not configured, logs server error and returns `{ success: false, code: 'SMTP_NOT_CONFIGURED' }`.
  - Controller receives failure, logs `[Auth] Verification email NOT delivered... (SMTP is not configured on the server)`.
  - Sets `emailSent: false`.
  - Returns HTTP 201 with an honest message explaining the account was created, but email could not be sent due to unconfigured mail server, advising to use Resend or contact the administrator.
- **Frontend Behavior:**
  - In `Register.jsx`, when registration succeeds (HTTP 201), it transitions to the post-registration screen.
  - *Observation:* Currently `Register.jsx` static text says *"We sent a secure verification link..."* regardless of `emailSent`. We need to pass `result.message` and `result.emailSent` through `AuthContext` to display the exact server message to the student.

### B. Resend Verification Link (`POST /api/auth/resend-verification`)
- **Inputs:** `email`.
- **Privacy & Account Enumeration:** Returns generic HTTP 200 response (`"If an unverified account exists with that email address, a new verification link has been sent."`) for both unknown and already-verified accounts, as required by security guidelines.
- **Cooldown Enforcement:** If `user.lastEmailVerificationSentAt` is within the last 30 seconds, immediately returns the generic response without creating tokens or triggering email.
- **Token Rotation & Send:**
  - Generates new 32-byte random hex token.
  - Updates `emailVerificationTokenHash` (SHA-256) and refreshes 24-hour expiration window.
  - Sets `lastEmailVerificationSentAt = new Date()`.
  - Calls `emailService.sendVerificationEmail(...)` within a try/catch, logging failures if delivery fails or SMTP is unconfigured.

### C. Verify Link (`GET` / `POST` `/api/auth/verify-email`)
- **Inputs:** `token`, `email` (via query string or body).
- **Missing Parameters:** Returns HTTP 400 `INVALID_PARAMETERS` if token or email is missing.
- **Non-existent User:** Returns HTTP 400 `USER_NOT_FOUND` if email is not found.
- **Already Verified:** If `user.emailVerified === true`, returns HTTP 200 `{ success: true, alreadyVerified: true, message: "Your email address is already verified. You can log in now." }`.
- **Token Expiry & Validity:**
  - Hashes incoming token with SHA-256.
  - Compares with stored `user.emailVerificationTokenHash`.
  - Checks `user.emailVerificationExpiresAt > Date.now()`.
  - If invalid or expired: returns HTTP 400 `TOKEN_EXPIRED` (*"The email verification link has expired or is invalid. Please request a new verification link."*).
- **Successful Verification:**
  - Sets `user.emailVerified = true`.
  - Unsets `emailVerificationTokenHash` and `emailVerificationExpiresAt`.
  - Saves user to MongoDB.
  - Returns HTTP 200 `{ success: true, message: "Email verified successfully! You can now log in to your account." }`.

### D. Login with Unverified Account (`POST /api/auth/login`)
- **Validation & Lockout:** Checks email/password presence, validates account lockout (HTTP 423), validates password match with bcrypt (HTTP 401 on mismatch, increments failed attempts).
- **Email Verification Gate:**
  - Evaluates `if (user.emailVerified === false)`.
  - Existing/legacy users whose `emailVerified` is `undefined` or `null` pass through and log in normally.
  - For unverified users (`emailVerified === false`), strictly returns HTTP 403:
    ```json
    {
      "success": false,
      "code": "EMAIL_NOT_VERIFIED",
      "message": "Your email address is not verified. Please check your inbox for the verification link.",
      "email": user.email
    }
    ```
- **Frontend Behavior (`Login.jsx`):**
  - Catches HTTP 403 `EMAIL_NOT_VERIFIED`.
  - Sets `unverifiedEmail = result.email || formData.email`.
  - Displays alert banner: *"Email not verified. Please click the link in your verification email before logging in."*
  - Renders a visible **"Resend Verification Link"** button with a 30-second cooldown timer. Clicking it triggers `apiService.resendVerification(unverifiedEmail)`.

### E. Login with Verified Account (`POST /api/auth/login`)
- Password matches and user is verified (`emailVerified !== false`).
- Resets `failedLoginAttempts = 0` and unsets `lockUntil`.
- Generates 15-minute JWT `accessToken`.
- Generates 40-byte random `rawRefreshToken`, hashes with SHA-256 into `user.refreshTokenHash`.
- Stores `rememberMe` flag (30-day cookie if checked, 7-day cookie if unchecked).
- Sets `refreshToken` httpOnly cookie on response.
- Returns HTTP 200 with user profile and access token.
- Frontend stores session and navigates to `/dashboard`.

---

## 3. Review of Existing Changes

1. **`backend/controllers/authController.js`**:
   - `registerUser` now checks `emailSent = !!(emailResult && emailResult.success && !emailResult.devMode)`.
   - Returns honest message when email is not sent.
   - `resendVerification` preserves the generic response required by tests, preventing user enumeration while logging server failures.
   - `loginUser` strictly checks `if (user.emailVerified === false)` so legacy accounts (`undefined`) continue to work.
   - Session duration respects `rememberMe`.
2. **`backend/scripts/delete_all_accounts.js`**:
   - Implements safe DRY RUN as default.
   - Requires `--confirm` flag to delete.
   - Preserves `Question` collection count.
   - We will refine the script to print the emails of accounts found during dry run as requested in Part 3.

---

## 4. Next Steps for Part 2 & Part 3

1. **Frontend Integration**:
   - Pass `emailSent` and `message` through `AuthContext.jsx`.
   - Update `Register.jsx` to display the exact server message on the post-registration screen, clearly indicating whether the email was sent or could not be delivered due to unconfigured SMTP.
2. **Cleanup Script Refinement**:
   - Review and ensure `backend/scripts/delete_all_accounts.js` prints the list of account emails in dry-run mode (without printing any password hashes or sensitive fields), backs up to `verification_runs/accounts_backup_<timestamp>.json` upon `--confirm`, and checks `Question` collection count before and after.
3. **Automated Testing**:
   - Update tests in `backend/tests/auth.test.js` to assert:
     - Active transport sends email (`emailSent: true`).
     - Unconfigured SMTP reports `emailSent: false` and returns clear non-deceptive message.
     - Transport send failure reports `emailSent: false` (not swallowed).
     - Token verifies account.
     - Unverified account is gated at login.
     - Legacy user (`emailVerified: undefined`) logs in without migration.
4. **Dry Run Execution**:
   - Run `node scripts/delete_all_accounts.js` in dry-run mode and capture full console output.
