package com.incaseof.app.di

import android.content.Context
import androidx.room.Room
import com.incaseof.app.data.dao.CaseDao
import com.incaseof.app.data.dao.CaseEventDao
import com.incaseof.app.data.db.InCaseOfDatabase
import com.incaseof.app.data.repositories.CaseRepository
import com.incaseof.app.data.repositories.CaseRepositoryImpl
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): InCaseOfDatabase {
        return Room.databaseBuilder(context, InCaseOfDatabase::class.java, "incaseof.db")
            .fallbackToDestructiveMigration(dropAllTables = true)
            .build()
    }

    @Provides
    fun provideCaseDao(db: InCaseOfDatabase): CaseDao = db.caseDao()

    @Provides
    fun provideCaseEventDao(db: InCaseOfDatabase): CaseEventDao = db.caseEventDao()

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
        prettyPrint = false
    }
}

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    @Binds
    @Singleton
    abstract fun bindCaseRepository(impl: CaseRepositoryImpl): CaseRepository
}
