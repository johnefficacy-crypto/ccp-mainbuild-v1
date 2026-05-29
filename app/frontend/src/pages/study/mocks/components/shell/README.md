# Attempt shell primitives

Controlled UI primitives for PR3 integration.

- `QuestionPalette`: numbered grid + keyboard navigation.
- `SectionTimer`/`CommonTimer`: server-authoritative countdown.
- `SubmitConfirmDialog`: explicit confirmation only.
- `AntiCheatProvider`: records fullscreen/visibility/copy-paste violations.

## Composition example

```jsx
<AntiCheatProvider enforceFullscreen blockCopy blockPaste onViolation={fn}>
  <CommonTimer expiresAt={expiresAt} onExpire={submit} />
  <QuestionPalette questions={questions} statusMap={statusMap} currentIndex={i} onJump={setI} />
</AntiCheatProvider>
```
