const express = require("express");
const multer = require("multer");
const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");
const path = require("path");

const app = express();
const upload = multer({ dest: "uploads/" });

// ✅ SERVE FRONTEND
app.use(express.static(path.join(__dirname, "../frontend/public")));

app.post("/upload", upload.array("documents"), async (req, res) => {
  try {
    console.log("📥 Files received:", req.files.length);

    const formData = new FormData();

    req.files.forEach(file => {
      console.log("➡️ Sending file to Flask:", file.originalname);
      formData.append(
        "documents",
        fs.createReadStream(file.path),
        file.originalname
      );
    });

    const response = await axios.post(
      "http://127.0.0.1:5000/verify",
      formData,
      {
        headers: formData.getHeaders(),
        timeout: 120000
      }
    );

    // 🧹 Cleanup
    req.files.forEach(file => {
      if (fs.existsSync(file.path)) fs.unlinkSync(file.path);
    });

    res.json(response.data);

  } catch (err) {
    console.error("❌ Node → Flask error:", err.message);

    res.status(500).json({
      error: "Verification failed",
      details: err.response?.data || err.message
    });
  }
});

app.listen(3000, () => {
  console.log("🚀 Node.js running on http://localhost:3000");
});
