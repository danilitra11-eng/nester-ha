# Nestor AI Butler — setup

## 1. Subscribe
Get a plan at **https://your-domain.com** (7-day free trial). Your license key arrives by email within a minute.

## 2. Install and open
Install the add-on, press **Start**, turn on **Show in sidebar**, and open **Nestor** from the sidebar.

## 3. The setup wizard (one minute)
1. **License key** — paste the key from your email.
2. **Name** — Nestor, Jarvis, Alfred… or anything you like.
3. **Personality** — Butler (polite, a touch of wit), Friendly (casual) or Brief (just the facts).
4. **Language** — Automatic answers in whatever language you speak, or pick a default.
5. **Permissions** — tap the kinds of devices Nestor may control. Everything else stays read-only. Locks and alarms are off unless you turn them on.
6. **Try it** — tap the suggested command to see it work on a real device in your home.

## 4. Change things later
Just ask: "be more casual", "call yourself Max", "answer in Spanish", "read your replies aloud", "quiet hours from 10 PM to 7 AM". Permissions are the exception: for safety they can only be changed from the ⚙︎ settings screen, never by chat.

Type, or tap 🎤 to speak. Tap 🔊 to hear replies aloud (never during quiet hours).

## What it costs
Your plan covers everything, including the AI. You don't need any API key or other paid service. Typing works on any connection. Voice input needs Home Assistant to be opened over HTTPS (Home Assistant Cloud or your own certificate).

## Privacy
To answer you, Nestor sends your message and the names and states of the devices it looks up to the Nestor service, which uses a large language model to decide what to do. Commands are carried out locally by this add-on. Nothing is stored after the reply except a monthly request count for billing. Full policy: https://your-domain.com/privacy

## Safety
- Domains like `homeassistant`, `shell_command` and `python_script` can never be called from chat.
- Locks and alarms are blocked unless you turn on `allow_security_devices`.
- Every action is shown under the reply (✓ done / ✗ blocked).

## Troubleshooting
| Message | Fix |
|---|---|
| License key not valid | Open ⚙︎ and re-paste the key. |
| Subscription not active | Renew from the link shown. |
| Key active on the maximum number of homes | Starter covers 1 Home Assistant installation, Family covers 2. Email support to move a key to a new machine. |
| Can't reach the server | Check the internet connection of your HA machine. |

Support: support@your-domain.com
