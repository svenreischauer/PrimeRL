# PrimeRL macOS App Packaging

This project can be packaged as a native macOS `.app` bundle with PyInstaller.

## Prerequisites
- macOS (Apple Silicon recommended)
- `python3` available on PATH
- Xcode command line tools (`codesign` available)

## Build `.app`
```bash
./release/scripts/build_app_macos.sh --version 1.3.3 --clean
```

Output (no databases):
- `release/PrimeRL_1.3.3_app_macos_arm64_nodb/dist/PrimeRL.app`

To include bundled databases:
```bash
./release/scripts/build_app_macos.sh --version 1.3.3 --clean --with-databases
```

## Sign `.app`
Ad-hoc signing (local testing):
```bash
./release/scripts/sign_app_macos.sh --app release/PrimeRL_1.3.3_app_macos_arm64_nodb/dist/PrimeRL.app
```

Developer ID signing (distribution):
```bash
./release/scripts/sign_app_macos.sh \
  --app release/PrimeRL_1.3.3_app_macos_arm64_nodb/dist/PrimeRL.app \
  --identity "Developer ID Application: Your Name (TEAMID)"
```

You can also build and sign in one call:
```bash
./release/scripts/build_app_macos.sh --version 1.3.3 --clean --sign
```

For distributable signing in one call:
```bash
./release/scripts/build_app_macos.sh \
  --version 1.3.3 --clean --sign \
  --sign-identity "Developer ID Application: Your Name (TEAMID)"
```

## Notarize + Staple (distribution)
Recommended auth setup once per machine (stores credentials in keychain):
```bash
xcrun notarytool store-credentials "PRIMERL_NOTARY" \
  --apple-id "you@example.com" \
  --team-id "TEAMID" \
  --password "<app-specific-password>"
```

Submit, wait, and staple:
```bash
./release/scripts/notarize_app_macos.sh \
  --app release/PrimeRL_1.3.3_app_macos_arm64_nodb/dist/PrimeRL.app \
  --keychain-profile PRIMERL_NOTARY
```

Fallback auth mode (without keychain profile):
```bash
./release/scripts/notarize_app_macos.sh \
  --app release/PrimeRL_1.3.3_app_macos_arm64_nodb/dist/PrimeRL.app \
  --apple-id "you@example.com" \
  --team-id "TEAMID" \
  --password "<app-specific-password>"
```

This script:
- optionally re-signs with `--sign-identity`
- zips the app for submission
- waits for notarization completion
- staples the ticket
- runs `spctl --assess` for Gatekeeper verification
