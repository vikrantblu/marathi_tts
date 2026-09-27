plugins {
    kotlin("jvm") version "2.4.20"
    id("org.openjfx.javafxplugin") version "0.1.0"
    application
}

group = "com.marathitts.desktop"
version = "1.0.0"

repositories {
    mavenCentral()
}

javafx {
    version = "21"
    modules = listOf("javafx.controls", "javafx.fxml", "javafx.media", "javafx.web", "javafx.swing")
}

dependencies {
    // Kotlin
    implementation(kotlin("stdlib"))
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-javafx:1.11.0")

    // JSON
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin:2.22.3")
    implementation("com.fasterxml.jackson.core:jackson-databind:2.22.3")

    // HTTP (for web-fetch fallback)
    implementation("com.squareup.okhttp3:okhttp:5.5.0")

    // Logging
    implementation("org.slf4j:slf4j-simple:2.0.20")

    // Testing
    testImplementation(kotlin("test"))
    testImplementation("org.junit.jupiter:junit-jupiter:6.1.3")
}

application {
    mainClass.set("com.marathitts.desktop.MainAppKt")
    applicationDefaultJvmArgs = listOf(
        "-Dfile.encoding=UTF-8",
        "-Dstdout.encoding=UTF-8",
        "-Dstderr.encoding=UTF-8"
    )
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
    jvmToolchain(17)
}

// Copy python_bridge resources into the jar
tasks.processResources {
    from("python_bridge") {
        into("python_bridge")
    }
}

// Fat jar for distribution
tasks.register<Jar>("fatJar") {
    archiveClassifier.set("all")
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    manifest {
        attributes["Main-Class"] = "com.marathitts.desktop.MainAppKt"
    }
    from(configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) })
    with(tasks.jar.get())
}
