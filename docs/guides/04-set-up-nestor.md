# Set up Nestor (one-minute wizard)

**What this does:** Connect Nestor to your subscription and choose its name, personality, language, permissions and voice.

## Before you start
- Your license key (from the email).
- Nestor is downloaded and Home Assistant was restarted.

## Steps
1. Open **Settings → Devices & services**, select **+ Add integration**, search for **Nestor** and select it.
   > 📷 *Screenshot: Add integration search*
2. **Step 1:** paste your license key and select **Submit**. Leave *Service address* as it is.
   > 📷 *Screenshot: step 1*
3. **Step 2:** pick a name (Nestor, Jarvis, Alfred…) or type your own.
   > 📷 *Screenshot: step 2*
4. **Step 3:** choose how it talks: Butler, Friendly or Brief.
5. **Step 4:** choose a language, or **Automatic** to answer in whatever language you speak.
6. **Step 5:** tick what Nestor may control. Untick anything you want read-only. Leave **Locks and alarm** unticked unless you're sure.
   > 📷 *Screenshot: permissions step*
7. **Step 6:** pick a voice, keep **Make Nestor my voice assistant** on, and select **Submit**.
   > 📷 *Screenshot: voice step*
8. Select **Finish**. **Nestor** now appears in the sidebar.

## How you know it worked
**Nestor** is in the sidebar. Open it and say "hello" — it answers using the name you chose.

## If it didn't work
| What you see | What to do |
|---|---|
| "That license key isn't valid" | Copy the key again from the email, with no spaces before or after. |
| "Can't reach the Nestor service" | Check that Home Assistant is online (Settings → System → Network). |
| "already used on the maximum number of homes" | Starter covers 1 home, Family 2. See *Move your key to a new Home Assistant*. |

Still stuck? Email **support@your-domain.com** with a screenshot of what you see.
