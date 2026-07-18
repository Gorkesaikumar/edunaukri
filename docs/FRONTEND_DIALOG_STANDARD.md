# Frontend Dialog Standard

This project does not use native browser dialogs in product UI.

## Never Use

- `alert()`
- `confirm()`
- `prompt()`
- `window.alert()`
- `window.confirm()`
- `window.prompt()`

## Use Instead

- Global dialog/toast service: `window.EduNotify`
- Source file: `static/js/edu-notify.js`

## Approved APIs

- `EduNotify.success(message, options?)`
- `EduNotify.error(message, options?)`
- `EduNotify.warning(message, options?)`
- `EduNotify.info(message, options?)`
- `EduNotify.toast(type, message, options?)`
- `EduNotify.ask(options)` for confirmations
- `EduNotify.input(options)` for typed input prompts
- `EduNotify.dialog(type, options)` for modal-style notices

## Template Confirmations

For forms that need confirmation, use declarative attributes:

- `data-edu-confirm`
- `data-edu-confirm-title`
- `data-edu-confirm-message`
- `data-edu-confirm-button`
- `data-edu-confirm-variant`

The global interceptor in `edu-notify.js` handles the dialog and submits on confirm.

## Accessibility Requirements

Dialog interactions must support:

- ESC close
- Enter confirm
- Focus trapping
- Proper ARIA labeling
- Keyboard-only navigation

## Design Requirements

All dialogs and toasts should match EduNaukri visual language:

- Rounded surfaces
- Soft shadow
- Subtle motion
- Responsive layout
- Tone-based iconography and actions
