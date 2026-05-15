package com.incaseof.app.di

import com.incaseof.app.BuildConfig
import com.incaseof.app.gemma.CasePlannerModel
import com.incaseof.app.gemma.GemmaCasePlanner
import com.incaseof.app.gemma.MockCasePlanner
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object GemmaModule {

    @Provides
    @Singleton
    fun provideCasePlanner(
        mockPlanner: MockCasePlanner,
        gemmaPlanner: GemmaCasePlanner
    ): CasePlannerModel {
        return if (BuildConfig.USE_MOCK_PLANNER) {
            mockPlanner
        } else {
            gemmaPlanner
        }
    }
}
