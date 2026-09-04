# Android demo release

The hackathon APK is a signed release of `com.incaof.app`. Release builds fail closed unless
the API, Cognito, Firebase and signing inputs are present, and the release variant sets
`ALLOW_LOCAL_DATA=false`.

## Protected inputs

Keep these outside Git:

- `android/app/google-services.json`, for the Firebase Android app `com.incaof.app`.
- A release JKS or keystore.
- `ICO_ANDROID_KEYSTORE_PASSWORD`, `ICO_ANDROID_KEY_ALIAS` and
  `ICO_ANDROID_KEY_PASSWORD`.

The `demo` GitHub environment stores the equivalent encrypted secrets and requires manual
approval before deployment. Never put a keystore, password, Firebase service-account key or
`google-services.json` in an APK download directory.

## Build

From `android/`:

```bash
export ICO_ANDROID_KEYSTORE_PATH=/absolute/path/to/ico-release.jks
export ICO_ANDROID_KEYSTORE_PASSWORD='<from your secret store>'
export ICO_ANDROID_KEY_ALIAS=ico-release
export ICO_ANDROID_KEY_PASSWORD='<from your secret store>'

./gradlew --no-daemon assembleRelease lintRelease ktlintCheck \
  -Pico.apiBaseUrl=https://api.incaof.com/ \
  -Pico.cognitoPoolId='<demo user pool id>' \
  -Pico.cognitoClientId='<demo app client id>' \
  -Pico.cognitoRegion=us-east-1
```

The output is `android/app/build/outputs/apk/release/app-release.apk`.

## Verify and install

Use the Android SDK build tools that match the checked-in build configuration:

```bash
apksigner verify --verbose --print-certs \
  android/app/build/outputs/apk/release/app-release.apk

aapt dump badging android/app/build/outputs/apk/release/app-release.apk
sha256sum android/app/build/outputs/apk/release/app-release.apk
adb install -r android/app/build/outputs/apk/release/app-release.apk
```

The accepted demo certificate SHA-256 fingerprint is
`F1:2D:18:90:54:5E:42:0F:5A:2E:10:FA:14:75:F2:1C:2F:A5:46:30:28:F5:7F:C3:64:3D:AA:1B:C4:2B:BD:62`.
Record the APK SHA-256, package metadata, device/API level, test exit status and install time in
`submission/release-evidence.json` for each accepted build.

## Judge installation

1. Download `in-case-of.apk` from the published `/downloads/` URL.
2. Compare its SHA-256 with `in-case-of.apk.sha256` beside the download.
3. Allow installation from the browser or file manager when Android prompts.
4. Install the APK, open **In Case Of**, and choose **Try judge demo**.

This is a hackathon demo distributed directly by the project, not a Google Play release and
not an emergency service.
