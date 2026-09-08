import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.android.application)
    // AGP 9 compiles Kotlin natively, so org.jetbrains.kotlin.android must NOT be applied.
    // Compiler plugins are still applied separately.
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ktlint)
}

// google-services.json is never committed — it is environment-specific and our rules forbid
// it (docs/SECURITY.md §7). Applying the plugin unconditionally would break every build
// that does not have it, including CI. Push is simply absent when the file is, and
// PushRegistration reports that rather than crashing.
val hasFirebaseConfig = file("google-services.json").exists()
if (hasFirebaseConfig) {
    apply(plugin = "com.google.gms.google-services")

    // The protected Firebase client is intentionally registered only for the signed
    // com.incaof.app release. The debug package has a different applicationId and must
    // remain push-disabled instead of trying to consume release credentials.
    tasks.matching { it.name == "processDebugGoogleServices" }.configureEach {
        enabled = false
    }
}

val configuredApiBaseUrl = project.findProperty("ico.apiBaseUrl") as String?
val configuredCognitoPoolId = project.findProperty("ico.cognitoPoolId") as String?
val configuredCognitoClientId = project.findProperty("ico.cognitoClientId") as String?
val releaseRequested = gradle.startParameter.taskNames.any { it.contains("Release", ignoreCase = true) }
val releaseKeystorePath = providers.environmentVariable("ICO_ANDROID_KEYSTORE_PATH").orNull
val releaseKeystorePassword = providers.environmentVariable("ICO_ANDROID_KEYSTORE_PASSWORD").orNull
val releaseKeyAlias = providers.environmentVariable("ICO_ANDROID_KEY_ALIAS").orNull
val releaseKeyPassword = providers.environmentVariable("ICO_ANDROID_KEY_PASSWORD").orNull

if (releaseRequested) {
    require(!configuredApiBaseUrl.isNullOrBlank()) { "Release requires -Pico.apiBaseUrl" }
    require(!configuredCognitoPoolId.isNullOrBlank()) { "Release requires -Pico.cognitoPoolId" }
    require(!configuredCognitoClientId.isNullOrBlank()) { "Release requires -Pico.cognitoClientId" }
    require(hasFirebaseConfig) { "Release requires app/google-services.json from the protected environment" }
    require(!releaseKeystorePath.isNullOrBlank()) { "Release requires ICO_ANDROID_KEYSTORE_PATH" }
    require(!releaseKeystorePassword.isNullOrBlank()) { "Release requires ICO_ANDROID_KEYSTORE_PASSWORD" }
    require(!releaseKeyAlias.isNullOrBlank()) { "Release requires ICO_ANDROID_KEY_ALIAS" }
    require(!releaseKeyPassword.isNullOrBlank()) { "Release requires ICO_ANDROID_KEY_PASSWORD" }
}

android {
    namespace = "com.incaof.app"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.incaof.app"
        minSdk = 26
        targetSdk = 37
        versionCode = 2
        versionName = "0.2.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Environment configuration, not secrets. Overridable from gradle.properties or CI
        // so dev, demo and prod builds point at their own stack.
        buildConfigField("String", "API_BASE_URL", "\"${prop("ico.apiBaseUrl", "https://api.incaof.com/")}\"")
        buildConfigField("String", "COGNITO_POOL_ID", "\"${prop("ico.cognitoPoolId", "")}\"")
        buildConfigField("String", "COGNITO_CLIENT_ID", "\"${prop("ico.cognitoClientId", "")}\"")
        buildConfigField("String", "COGNITO_REGION", "\"${prop("ico.cognitoRegion", "us-east-1")}\"")
        buildConfigField("boolean", "HAS_PUSH", "false")
        buildConfigField("boolean", "ALLOW_LOCAL_DATA", "true")
    }

    signingConfigs {
        if (
            !releaseKeystorePath.isNullOrBlank() &&
            !releaseKeystorePassword.isNullOrBlank() &&
            !releaseKeyAlias.isNullOrBlank() &&
            !releaseKeyPassword.isNullOrBlank()
        ) {
            create("release") {
                storeFile = file(releaseKeystorePath)
                storePassword = releaseKeystorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
                enableV1Signing = true
                enableV2Signing = true
                enableV3Signing = true
                enableV4Signing = true
            }
        }
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
        }
        release {
            buildConfigField("boolean", "ALLOW_LOCAL_DATA", "false")
            buildConfigField("boolean", "HAS_PUSH", hasFirebaseConfig.toString())
            signingConfig = signingConfigs.findByName("release")
            isMinifyEnabled = true
            // Shrinking code without shrinking resources leaves the unused half behind.
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // Amplify requires it. It also backfills java.time, which this app uses throughout
        // for plan timezones — worth having regardless of who asked for it.
        isCoreLibraryDesugaringEnabled = true
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    lint {
        warningsAsErrors = false
        abortOnError = true
        // Adaptive icons must live in mipmap-anydpi-v26 even at minSdk 26: the plain
        // `anydpi` qualifier does not resolve, and AAPT fails outright. The check is right
        // in general and wrong for this specific folder.
        disable += "ObsoleteSdkInt"
    }

    packaging {
        resources.excludes += setOf("/META-INF/{AL2.0,LGPL2.1}", "META-INF/versions/9/OSGI-INF/MANIFEST.MF")
    }

    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

ktlint {
    version.set("1.8.0")
    android.set(true)
    filter {
        exclude { it.file.path.contains("/core/design/Tokens.kt") }
        exclude { it.file.path.contains("/build/") }
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

/** Reads a build property, falling back to a default so a fresh clone builds without setup. */
fun prop(name: String, fallback: String): String = (project.findProperty(name) as String?) ?: fallback

dependencies {
    coreLibraryDesugaring(libs.desugar.jdk.libs)

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.core.splashscreen)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.serialization.json)

    implementation(libs.retrofit)
    implementation(libs.retrofit.serialization)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)

    implementation(libs.amplify.core.kotlin)
    implementation(libs.amplify.auth.cognito)

    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)

    val composeBom = platform(libs.androidx.compose.bom)
    implementation(composeBom)
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.core)

    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)

    androidTestImplementation(composeBom)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.ui.test.junit4)
}
