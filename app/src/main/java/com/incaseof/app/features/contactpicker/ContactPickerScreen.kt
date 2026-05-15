package com.incaseof.app.features.contactpicker

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.incaseof.app.core.design.*
import com.incaseof.app.data.repositories.CaseRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ContactPickerUiState(
    val name: String = "",
    val phone: String = "",
    val email: String = "",
    val relationship: String = "",
    val isSaving: Boolean = false,
    val isSaved: Boolean = false
)

@HiltViewModel
class ContactPickerViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val caseRepository: CaseRepository
) : ViewModel() {

    private val caseId: String = savedStateHandle["caseId"] ?: ""
    private val _uiState = MutableStateFlow(ContactPickerUiState())
    val uiState = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            caseRepository.getCase(caseId)?.let { case ->
                _uiState.update {
                    it.copy(
                        name = case.trustedContactName ?: "",
                        phone = case.trustedContactPhone ?: "",
                        email = case.trustedContactEmail ?: "",
                        relationship = case.trustedContactRelationship ?: ""
                    )
                }
            }
        }
    }

    fun updateName(value: String) = _uiState.update { it.copy(name = value) }
    fun updatePhone(value: String) = _uiState.update { it.copy(phone = value) }
    fun updateEmail(value: String) = _uiState.update { it.copy(email = value) }
    fun updateRelationship(value: String) = _uiState.update { it.copy(relationship = value) }

    fun save() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true) }
            caseRepository.updateTrustedContact(
                id = caseId,
                name = _uiState.value.name.ifBlank { null },
                phone = _uiState.value.phone.ifBlank { null },
                email = _uiState.value.email.ifBlank { null },
                relationship = _uiState.value.relationship.ifBlank { null }
            )
            _uiState.update { it.copy(isSaving = false, isSaved = true) }
        }
    }

    fun isValid(): Boolean {
        val state = _uiState.value
        return state.name.isNotBlank() && (state.phone.isNotBlank() || state.email.isNotBlank())
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ContactPickerScreen(
    onContactSelected: () -> Unit,
    onBack: () -> Unit,
    viewModel: ContactPickerViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(uiState.isSaved) {
        if (uiState.isSaved) onContactSelected()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Trusted Contact", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            SafetyCard {
                Column {
                    Icon(
                        Icons.Default.PersonAdd,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(32.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Who should be contacted?",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Add the person who should receive your safety alert.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            OutlinedTextField(
                value = uiState.name,
                onValueChange = viewModel::updateName,
                label = { Text("Contact name") },
                leadingIcon = { Icon(Icons.Default.Person, null) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                singleLine = true
            )

            OutlinedTextField(
                value = uiState.phone,
                onValueChange = viewModel::updatePhone,
                label = { Text("Phone number") },
                leadingIcon = { Icon(Icons.Default.Phone, null) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                singleLine = true
            )

            OutlinedTextField(
                value = uiState.email,
                onValueChange = viewModel::updateEmail,
                label = { Text("Email (optional)") },
                leadingIcon = { Icon(Icons.Default.Email, null) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                singleLine = true
            )

            OutlinedTextField(
                value = uiState.relationship,
                onValueChange = viewModel::updateRelationship,
                label = { Text("Relationship (e.g., mother, partner, friend)") },
                leadingIcon = { Icon(Icons.Default.Group, null) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(8.dp))

            PrimaryCTA(
                text = if (uiState.isSaving) "Saving..." else "Save contact",
                onClick = { viewModel.save() },
                enabled = viewModel.isValid() && !uiState.isSaving,
                icon = Icons.Default.Check
            )
        }
    }
}
