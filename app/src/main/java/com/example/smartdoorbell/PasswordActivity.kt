package com.example.smartdoorbell

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.google.firebase.database.FirebaseDatabase
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.create

class PasswordActivity : AppCompatActivity() {
    val currentIp = AppState.getInstance().ip
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_password)
        val passwordEditText = findViewById<EditText>(R.id.passwordEditText);


        try {
            val database = FirebaseDatabase.getInstance()
            val reference = database.reference.child("password")
            //reference.setValue("1234")
            reference.get().addOnSuccessListener {
                val pass = it.value.toString()
                println("Retrieved value: $pass")
                passwordEditText.setText(pass)
            }.addOnFailureListener {
                println("Error: ${it.message}")
            }
        }catch (e: Exception){
            println("ERROR")
            println(e.printStackTrace())
        }

        val saveButton = findViewById<Button>(R.id.saveButton)
        saveButton.setOnClickListener { // Create an intent to navigate to SecondActivity

            try {
                val database = FirebaseDatabase.getInstance()
                val reference = database.reference.child("password")
                reference.setValue(passwordEditText.text.toString());
            }catch (e: Exception)
            {
                println(e.printStackTrace())
            }
            val intent = Intent(
                this@PasswordActivity,
                MainActivity::class.java
            )
            startActivity(intent)
        }

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
    }
}