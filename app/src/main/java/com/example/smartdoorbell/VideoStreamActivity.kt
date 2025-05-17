package com.example.smartdoorbell

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.longdo.mjpegviewer.MjpegView

class VideoStreamActivity : AppCompatActivity() {
    val currentIp = AppState.getInstance().ip

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_video_stream)

        val viewer = findViewById<View>(R.id.mjpegview) as MjpegView
        viewer.mode = MjpegView.MODE_FIT_WIDTH
        viewer.isAdjustHeight = true
        viewer.supportPinchZoomAndPan = true
        viewer.setUrl("http://$currentIp:8000/stream.mjpg")
        viewer.startStream()
    }
}