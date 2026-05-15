package com.incaseof.app.gemma

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Manages LiteRT-LM engine lifecycle for Gemma 4 E2B on-device inference.
 *
 * Uses the official LiteRT-LM 0.11.0 Kotlin API:
 *   - Engine: entry point, initialized with EngineConfig
 *   - Conversation: stateful chat session with streaming via Flow
 *   - ConversationConfig: system instruction, sampler settings
 *
 * To enable real Gemma inference:
 * 1. Uncomment LiteRT-LM dependency in build.gradle.kts
 * 2. Push model: adb push gemma-4-E2B-it.litertlm /data/local/tmp/llm/
 *    Or copy to app filesDir on first launch
 * 3. Set USE_MOCK_PLANNER=false in build config
 *
 * API Reference: https://ai.google.dev/edge/litert-lm/android
 */
@Singleton
class GemmaEngineProvider @Inject constructor(
    @ApplicationContext private val context: Context
) {
    // Engine state
    private var isInitialized = false
    private var initError: String? = null

    // When LiteRT-LM is enabled, these hold the real instances:
    // private var engine: com.google.ai.edge.litertlm.Engine? = null

    /**
     * Check if the model file exists on device.
     * Checks both the configured path and the app's internal filesDir.
     */
    fun isModelAvailable(): Boolean {
        return try {
            val configuredPath = com.incaseof.app.BuildConfig.MODEL_PATH
            val internalPath = "${context.filesDir.absolutePath}/gemma-4-E2B-it.litertlm"
            java.io.File(configuredPath).exists() || java.io.File(internalPath).exists()
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Resolve the actual model path, preferring internal storage.
     */
    private fun resolveModelPath(): String {
        val internalPath = "${context.filesDir.absolutePath}/gemma-4-E2B-it.litertlm"
        if (java.io.File(internalPath).exists()) return internalPath
        return com.incaseof.app.BuildConfig.MODEL_PATH
    }

    /**
     * Initialize the LiteRT-LM engine. Call on a background thread/coroutine.
     *
     * Official API (LiteRT-LM 0.11.0):
     * ```
     * val engineConfig = EngineConfig(
     *     modelPath = resolveModelPath(),
     *     backend = Backend.CPU(),  // Or Backend.GPU()
     *     cacheDir = context.cacheDir.path
     * )
     * engine = Engine(engineConfig)
     * engine.initialize()  // Can take up to 10 seconds
     * ```
     */
    suspend fun initialize(): Boolean {
        return try {
            if (!isModelAvailable()) {
                initError = "Model file not found. Push model with: " +
                    "adb push gemma-4-E2B-it.litertlm /data/local/tmp/llm/"
                return false
            }

            // === Real LiteRT-LM initialization (uncomment when dependency is enabled) ===
            // val modelPath = resolveModelPath()
            // val engineConfig = com.google.ai.edge.litertlm.EngineConfig(
            //     modelPath = modelPath,
            //     backend = com.google.ai.edge.litertlm.Backend.CPU(),
            //     cacheDir = context.cacheDir.path
            // )
            // engine = com.google.ai.edge.litertlm.Engine(engineConfig)
            // engine!!.initialize()
            // ============================================================================

            isInitialized = true
            true
        } catch (e: Exception) {
            initError = "Engine initialization failed: ${e.message}"
            false
        }
    }

    fun isReady(): Boolean = isInitialized
    fun getError(): String? = initError

    /**
     * Generate a response from the on-device Gemma model.
     *
     * Official API (LiteRT-LM 0.11.0) — synchronous version:
     * ```
     * val conversationConfig = ConversationConfig(
     *     systemInstruction = Contents.of(PromptTemplates.SYSTEM_PROMPT),
     *     samplerConfig = SamplerConfig(topK = 10, topP = 0.95, temperature = 0.7)
     * )
     * engine!!.createConversation(conversationConfig).use { conversation ->
     *     val response = conversation.sendMessage(prompt)
     *     return response.text ?: ""
     * }
     * ```
     *
     * Streaming version (recommended for UX):
     * ```
     * engine!!.createConversation(conversationConfig).use { conversation ->
     *     val chunks = mutableListOf<String>()
     *     conversation.sendMessageAsync(prompt)
     *         .catch { e -> throw e }
     *         .collect { message -> chunks.add(message.toString()) }
     *     return chunks.joinToString("")
     * }
     * ```
     */
    suspend fun generate(prompt: String): String {
        if (!isInitialized) {
            throw IllegalStateException("Engine not initialized. Call initialize() first.")
        }

        // === Real LiteRT-LM generation (uncomment when dependency is enabled) ===
        // val conversationConfig = com.google.ai.edge.litertlm.ConversationConfig(
        //     systemInstruction = com.google.ai.edge.litertlm.Contents.of(
        //         PromptTemplates.SYSTEM_PROMPT
        //     ),
        //     samplerConfig = com.google.ai.edge.litertlm.SamplerConfig(
        //         topK = 10,
        //         topP = 0.95f,
        //         temperature = 0.7f
        //     )
        // )
        // engine!!.createConversation(conversationConfig).use { conversation ->
        //     val response = conversation.sendMessage(prompt)
        //     return response.text ?: ""
        // }
        // ========================================================================

        throw UnsupportedOperationException(
            "Real Gemma inference not yet enabled. Use MockCasePlanner."
        )
    }

    /**
     * Release engine resources.
     * Call when the app is being destroyed or the engine is no longer needed.
     */
    fun shutdown() {
        // engine?.close()
        // engine = null
        isInitialized = false
    }
}
