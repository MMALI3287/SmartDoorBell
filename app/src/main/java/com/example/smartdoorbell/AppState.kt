package com.example.smartdoorbell

import androidx.compose.runtime.mutableStateOf

class AppState {
    private val _ip = mutableStateOf("")
    val ip: String get() = _ip.value

    fun updateIp(newIp: String) {
        _ip.value = newIp
    }

    companion object {
        private var instance: AppState? = null

        fun getInstance(): AppState {
            if (instance == null) {
                instance = AppState()
            }
            return instance!!
        }
    }
}