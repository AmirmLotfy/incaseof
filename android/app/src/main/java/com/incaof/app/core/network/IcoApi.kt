package com.incaof.app.core.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * The API, as the app uses it.
 *
 * Only the routes this client actually calls. Adding a method here means adding a route in
 * infra/cdk/lib/constructs/api.ts — a template assertion checks the two agree, because a
 * client calling a route that was never deployed fails at the worst possible moment.
 */
interface IcoApi {
    @GET("v1/moments/next")
    suspend fun nextMoment(): Response<MomentDto>

    /**
     * "I'm okay."
     *
     * [source] distinguishes a tap in the app from a tap on the notification, because the
     * resolution record keeps both the method and where it physically came from.
     */
    @POST("v1/moments/{momentId}/confirm")
    suspend fun confirmMoment(
        @Path("momentId") momentId: String,
        @Header("x-ico-source") source: String = "app",
        @Header("Idempotency-Key") idempotencyKey: String,
    ): Response<ConfirmResponseDto>

    @POST("v1/moments/{momentId}/extend")
    suspend fun extendMoment(
        @Path("momentId") momentId: String,
        @Body request: ExtendRequest,
    ): Response<MomentDto>

    @GET("v1/plans")
    suspend fun plans(): Response<List<PlanDto>>

    @GET("v1/plans/{planId}")
    suspend fun plan(
        @Path("planId") planId: String,
    ): Response<PlanDto>

    @GET("v1/circle")
    suspend fun circle(): Response<List<CircleMemberDto>>

    @POST("v1/alerts/{alertId}/claim")
    suspend fun claimAlert(
        @Path("alertId") alertId: String,
        @Header("Idempotency-Key") idempotencyKey: String,
    ): Response<ClaimResponseDto>

    @GET("v1/alerts/{alertId}/timeline")
    suspend fun timeline(
        @Path("alertId") alertId: String,
    ): Response<TimelineDto>
}

@kotlinx.serialization.Serializable
data class ExtendRequest(
    val seconds: Int,
)
