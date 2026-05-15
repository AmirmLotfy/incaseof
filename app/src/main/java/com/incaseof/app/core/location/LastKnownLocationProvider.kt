package com.incaseof.app.core.location

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.suspendCancellableCoroutine
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume

@Singleton
class LastKnownLocationProvider @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val fusedClient = LocationServices.getFusedLocationProviderClient(context)

    /**
     * Get last known location, or null if unavailable or permission not granted.
     * Caller must ensure location permission is granted before calling.
     */
    @SuppressLint("MissingPermission")
    suspend fun getLastKnownLocationOrNull(): Location? {
        return try {
            suspendCancellableCoroutine { cont ->
                val tokenSource = CancellationTokenSource()
                cont.invokeOnCancellation { tokenSource.cancel() }

                fusedClient.getCurrentLocation(
                    Priority.PRIORITY_BALANCED_POWER_ACCURACY,
                    tokenSource.token
                ).addOnSuccessListener { location ->
                    cont.resume(location)
                }.addOnFailureListener {
                    cont.resume(null)
                }
            }
        } catch (e: Exception) {
            null
        }
    }
}
