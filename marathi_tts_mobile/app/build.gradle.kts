import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "com.marathitts.mobile"
    compileSdk = 34

    // ── Signing config loaded from keystore.properties (not committed to git) ──
    val keystoreProps = Properties()
    val keystoreFile = rootProject.file("keystore.properties")
    if (keystoreFile.exists()) keystoreProps.load(keystoreFile.inputStream())

    defaultConfig {
        applicationId = "com.marathitts.mobile"
        minSdk = 26
        targetSdk = 34
        versionCode = 10
        versionName = "5.2.0"

        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    buildFeatures {
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    signingConfigs {
        create("release") {
            if (keystoreProps.isNotEmpty()) {
                storeFile     = file(keystoreProps["storeFile"] as String)
                storePassword = keystoreProps["storePassword"] as String
                keyAlias      = keystoreProps["keyAlias"] as String
                keyPassword   = keystoreProps["keyPassword"] as String
            }
        }
    }

    buildTypes {
        getByName("release") {
            signingConfig      = signingConfigs.getByName("release")
            isMinifyEnabled    = true          // R8 code shrinking
            isShrinkResources  = true          // remove unused resources
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}

// ── Chaquopy: Python 3.11 bundled inside the APK ────────────────────────────
chaquopy {
    defaultConfig {
        version = "3.11"
        buildPython("D:\\marathi_tts\\marathi_tts_web\\.venv\\Scripts\\python.exe")

        pip {
            // Pure-Python packages (safe for Chaquopy cross-compile)
            install("gtts==2.5.0")
            install("edge-tts==6.1.9")         // Microsoft neural voices (ManoharNeural male / AarohiNeural female)
            install("requests==2.31.0")
            install("beautifulsoup4==4.12.2")
            install("PyPDF2==3.0.1")
            install("pydub==0.25.1")
            install("click==8.2.1")           // required by typer (indic-transliteration dep)
            install("indic-transliteration==2.3.39")
            // Note: Pillow requires native zlib on build host - not available via Windows venv.
            // Image OCR in web_bridge.py is skipped gracefully when PIL is absent.
            // Note: Pillow, pytesseract, PyMuPDF, pyttsx3 require native builds
            // and are not compatible with Chaquopy. OCR uses Android ML Kit instead.
        }
    }
    sourceSets {
        getByName("main") {
            srcDir("src/main/python")
        }
    }
}

dependencies {
    // AndroidX core
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")

    // Navigation Component
    implementation("androidx.navigation:navigation-fragment-ktx:2.7.6")
    implementation("androidx.navigation:navigation-ui-ktx:2.7.6")

    // Lifecycle (ViewModel + LiveData)
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-livedata-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")

    // Kotlin Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    // JSON
    implementation("com.google.code.gson:gson:2.10.1")

    // File picker / image selection
    implementation("androidx.activity:activity-ktx:1.8.2")
    implementation("androidx.fragment:fragment-ktx:1.6.2")

    // RecyclerView & CardView
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.cardview:cardview:1.0.0")

    // MediaPlayer wrapper
    implementation("androidx.media:media:1.7.0")

    // Network (OkHttp for web-fetch)
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // ML Kit Text Recognition — Devanagari (Marathi, Hindi)
    // Used for native PDF OCR via PdfRenderer on image-based PDFs
    implementation("com.google.mlkit:text-recognition-devanagari:16.0.1")

    // CameraX — custom camera with book alignment overlay
    val cameraxVersion = "1.3.1"
    implementation("androidx.camera:camera-core:$cameraxVersion")
    implementation("androidx.camera:camera-camera2:$cameraxVersion")
    implementation("androidx.camera:camera-lifecycle:$cameraxVersion")
    implementation("androidx.camera:camera-view:$cameraxVersion")

    // ExifInterface — reads JPEG rotation tags so captured photos are upright
    implementation("androidx.exifinterface:exifinterface:1.3.7")

    // Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}
