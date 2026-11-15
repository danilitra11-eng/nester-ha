# Connect Telegram

**What this does:** Talk to your home from anywhere by Telegram message or voice note.

## Before you start
- Telegram installed on your phone.
- You're an administrator in Home Assistant.

## Steps
1. Open **Nestor** in the sidebar → **⚙︎ Settings** → **Telegram** → **Connect Telegram**. A 6-digit code appears.
   > 📷 *Screenshot: code on screen*
2. On your phone, open Telegram and search for **@NestorHomeBot** (the name is shown next to the code). Open it.
   > 📷 *Screenshot: bot in Telegram search*
3. Tap **Start**, then send the 6-digit code.
   > 📷 *Screenshot: chat with the code*
4. Wait for the reply **Connected ✓**.
5. Each family member who wants to use it repeats steps 1–4 with a new code.

## How you know it worked
Send "are the lights on?" in Telegram and get an answer about your home.

## If it didn't work
| What you see | What to do |
|---|---|
| "That code didn't work" | Codes last 10 minutes and work once. Create a new one in step 1. |
| No answer to messages | Check Home Assistant is online and Nestor's status line (top of the Nestor panel) has no error. |
| Voice notes get "couldn't understand" | Your Home Assistant needs speech-to-text: add **Whisper** or Home Assistant Cloud in Settings → Voice assistants. |

Still stuck? Email **support@your-domain.com** with a screenshot of what you see.
