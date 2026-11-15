# Nestor AI Butler for Home Assistant

Talk to your home like a person — in any language, by text, voice or Telegram.

- **Controls your devices**: "turn off everything downstairs and set the bedroom to 70".
- **Edits your home's structure**: creates rooms and floors, moves and renames devices.
- **Designs dashboards and themes** on request, with undo.
- **Talks back** in a voice you choose, from the Home Assistant app, your watch, voice speakers, or Telegram.
- **You set the limits**: choose what it may control; locks and alarms are off by default; it always asks before deleting anything.

Requires a Nestor subscription (7-day free trial): **https://your-domain.com**

## Install

1. In Home Assistant: **Settings → Marketplace**, search **Nestor**, **Download** — or **⋮ → Add from a GitHub link** and paste `https://github.com/danilitra11-eng/nester-ha`.
2. Restart Home Assistant.
3. **Settings → Devices & services → + Add integration → Nestor**, and follow the one-minute wizard.

Step-by-step guides with screenshots: [docs/guides](docs/guides/README.md)

## Privacy

To answer you, Nestor sends your message and the names and states of the devices involved to the Nestor service. Actions run locally in your Home Assistant, under the permissions you set.
