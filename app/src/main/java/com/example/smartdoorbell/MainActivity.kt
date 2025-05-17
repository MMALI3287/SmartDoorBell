package com.example.smartdoorbell

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.ktx.Firebase
import com.google.firebase.messaging.ktx.messaging
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.create
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine


class MainActivity : AppCompatActivity() {
    private lateinit var api: FcmApi
    private lateinit var checkVideoButton: Button
    private lateinit var callButton: Button
    private lateinit var passwordButton: Button
    private lateinit var addFaceButton: Button
    private lateinit var trainButton: Button
    private lateinit var unlockButton: Button
    private val appState = AppState.getInstance()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNotificationPermission()
        setContentView(R.layout.activity_main)



        initializeViews()
        initializeApi()
    }

    private fun initializeViews() {
        checkVideoButton = findViewById(R.id.checkVideoButton)
        callButton = findViewById(R.id.callButton)
        passwordButton = findViewById(R.id.passwordButton)
        addFaceButton = findViewById(R.id.addFaceButton)
        trainButton = findViewById(R.id.trainButton)
        unlockButton = findViewById(R.id.unlockButton)

        // Disable buttons until API is initialized
        setButtonsEnabled(false)
    }

    private fun initializeApi() {
        val okHttpClient = OkHttpClient.Builder()
            .connectTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .callTimeout(60, TimeUnit.SECONDS)
            .build()

        lifecycleScope.launch {
            try {
                // Get IP synchronously using coroutines
                val ip = suspendCoroutine<String> { continuation ->
                    FirebaseDatabase.getInstance()
                        .reference
                        .child("ip")
                        .get()
                        .addOnSuccessListener {
                            continuation.resume(it.value.toString())

                        }
                        .addOnFailureListener {
                            continuation.resumeWithException(it)
                        }
                }
                appState.updateIp(ip)
                // Initialize Retrofit with IP
                api = Retrofit.Builder()
                    .baseUrl("http://$ip:8000")
                    .client(okHttpClient)
                    .addConverterFactory(MoshiConverterFactory.create())
                    .build()
                    .create()

                // Register FCM token
                val localToken = Firebase.messaging.token.await()
                api.token(TokenBody(localToken))

                // Enable buttons after initialization
                setButtonsEnabled(true)
                setupButtonClickListeners()

            } catch (e: Exception) {
                Toast.makeText(
                    this@MainActivity,
                    "Failed to initialize: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
                e.printStackTrace()
            }
        }
    }

    private fun setButtonsEnabled(enabled: Boolean) {
        checkVideoButton.isEnabled = enabled
        callButton.isEnabled = enabled
        passwordButton.isEnabled = enabled
        addFaceButton.isEnabled = enabled
        trainButton.isEnabled = enabled
        unlockButton.isEnabled = enabled
    }

    private fun setupButtonClickListeners() {
        checkVideoButton.setOnClickListener {
            startActivity(Intent(this, VideoStreamActivity::class.java))
        }

        passwordButton.setOnClickListener {
            startActivity(Intent(this, PasswordActivity::class.java))
        }

        addFaceButton.setOnClickListener {
            startActivity(Intent(this, AddFaceActivity::class.java))
        }

        trainButton.setOnClickListener {
            performApiAction("Training") { api.train() }
        }

        unlockButton.setOnClickListener {
            performApiAction("Unlock") { api.unlock() }
        }
    }

    private fun performApiAction(
        actionName: String,
        action: suspend () -> retrofit2.Response<*>
    ) {
        val progressDialog = CustomProgressDialog(this)
        progressDialog.show()

        lifecycleScope.launch {
            try {
                val response = action()
                val message = if (response.isSuccessful) {
                    "$actionName Successful"
                } else {
                    "$actionName Failed"
                }
                Toast.makeText(this@MainActivity, message, Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                e.printStackTrace()
                Toast.makeText(
                    this@MainActivity,
                    "$actionName Failed",
                    Toast.LENGTH_SHORT
                ).show()
            } finally {
                progressDialog.dismiss()
            }
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val hasPermission = ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED

            if (!hasPermission) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    0
                )
            }
        }
    }
}