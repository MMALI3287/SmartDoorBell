package com.example.smartdoorbell

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.ktx.Firebase
import com.google.firebase.messaging.ktx.messaging
import com.longdo.mjpegviewer.MjpegView
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.create

class AddFaceActivity : AppCompatActivity() {
    val currentIp = AppState.getInstance().ip
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_add_face)
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }


        val api: FcmApi = Retrofit.Builder()
            .baseUrl("http://$currentIp:8000")
            .addConverterFactory(MoshiConverterFactory.create())
            .build()
            .create()

        val viewer = findViewById<View>(R.id.mjpegview) as MjpegView
        viewer.mode = MjpegView.MODE_FIT_WIDTH
        viewer.isAdjustHeight = true
        viewer.supportPinchZoomAndPan = true
        viewer.setUrl("http://$currentIp:8000/stream.mjpg")
        viewer.startStream()


        val nameEditText = findViewById<EditText>(R.id.nameEditText);

        val captureButton = findViewById<Button>(R.id.captureButton)
        captureButton.setOnClickListener {
            val name = nameEditText.text.toString()
            if(name.isNotEmpty() && name.isNotBlank() && name.length > 3){
                lifecycleScope.launch {
                    try {
                        println("CALLED")
                        api.capture(CaptureBody(name))
                        println("SUCC")

                    } catch (e: Exception) {
                        println(e.printStackTrace())
                    }
                }
            }
        }
    }
}