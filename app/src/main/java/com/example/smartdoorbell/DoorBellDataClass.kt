package com.example.smartdoorbell

data class SendMessageDto(
    val to: String?,
    val notification: NotificationBody
)

data class NotificationBody(
    val title: String,
    val body:String
)

data class TokenBody(
    val token: String
)

data class CaptureBody(
    val name: String
)

