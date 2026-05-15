package com.incaseof.app.navigation

/**
 * All navigation routes in the app.
 */
sealed class Routes(val route: String) {
    object Splash : Routes("splash")
    object Onboarding : Routes("onboarding")
    object Home : Routes("home")
    object CreateCase : Routes("create_case")
    object Compiling : Routes("compiling/{condition}/{action}") {
        fun createRoute(condition: String, action: String): String {
            val enc = java.net.URLEncoder.encode(condition, "UTF-8")
            val encA = java.net.URLEncoder.encode(action, "UTF-8")
            return "compiling/$enc/$encA"
        }
    }
    object Review : Routes("review/{caseId}") {
        fun createRoute(caseId: String) = "review/$caseId"
    }
    object ContactPicker : Routes("contact_picker/{caseId}") {
        fun createRoute(caseId: String) = "contact_picker/$caseId"
    }
    object CaseDetail : Routes("case_detail/{caseId}") {
        fun createRoute(caseId: String) = "case_detail/$caseId"
    }
    object Simulation : Routes("simulation/{caseId}") {
        fun createRoute(caseId: String) = "simulation/$caseId"
    }
    object EmergencyLog : Routes("emergency_log")
    object Settings : Routes("settings")
    object About : Routes("about")
    object ActionReview : Routes("action_review/{caseId}") {
        fun createRoute(caseId: String) = "action_review/$caseId"
    }
}
