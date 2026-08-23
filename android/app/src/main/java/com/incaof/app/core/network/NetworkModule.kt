package com.incaof.app.core.network

import com.incaof.app.BuildConfig
import com.incaof.app.core.auth.AuthRepository
import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/**
 * HTTP.
 *
 * Deliberate choices:
 *
 * Timeouts are short. This app's calls happen while somebody is waiting to say they are
 * okay; a request hanging for 60 seconds is worse than one that fails fast and lets the
 * UI offer the action again.
 *
 * Logging never records bodies, even in debug. Responses carry plan and alert detail, and
 * a logcat transcript of who is alone and when is exactly the data this product exists to
 * protect. Headers are excluded too — that is where the bearer token lives.
 */
object NetworkModule {
    private val json =
        Json {
            ignoreUnknownKeys = true
            explicitNulls = false
        }

    fun api(auth: AuthRepository): IcoApi =
        Retrofit
            .Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(client(auth))
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(IcoApi::class.java)

    private fun client(auth: AuthRepository): OkHttpClient =
        OkHttpClient
            .Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .addInterceptor(BearerTokenInterceptor(auth))
            .apply {
                if (BuildConfig.DEBUG) {
                    addInterceptor(
                        HttpLoggingInterceptor().apply {
                            level = HttpLoggingInterceptor.Level.BASIC
                        },
                    )
                }
            }.build()
}

/**
 * Attaches the Cognito access token.
 *
 * Blocking on purpose: OkHttp interceptors are synchronous, and a token fetched off-thread
 * here would race the request it is meant to authorise.
 */
class BearerTokenInterceptor(
    private val auth: AuthRepository,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): okhttp3.Response {
        val token = auth.currentAccessTokenBlocking()
        val request =
            if (token != null) {
                chain
                    .request()
                    .newBuilder()
                    .addHeader("Authorization", "Bearer $token")
                    .build()
            } else {
                chain.request()
            }
        return chain.proceed(request)
    }
}
