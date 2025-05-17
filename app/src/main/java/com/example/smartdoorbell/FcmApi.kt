package com.example.smartdoorbell

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

interface FcmApi {

    @POST("/send")
    suspend fun sendMessage(
        @Body message: SendMessageDto

    )

    @POST("/broadcast")
    suspend fun broadcast(
        @Body message: SendMessageDto
    )

    @POST("/token")
    suspend fun token(
        @Body message: TokenBody
    )

    @POST("/capture")
    suspend fun capture(
        @Body message: CaptureBody
    )

    @POST("/train")
    suspend fun train(

    ): Response<Unit>

    @POST("/unlock")
    suspend fun unlock(

    ): Response<Unit>
}