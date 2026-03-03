/**
 * Node.js Backend Server
 * Handles file uploads and proxies to Flask API
 */

const express = require('express');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Configure multer for file uploads
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadDir = './uploads';
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, uniqueSuffix + '-' + file.originalname);
    }
});

const upload = multer({
    storage: storage,
    limits: {
        fileSize: 50 * 1024 * 1024 // 50MB limit
    },
    fileFilter: (req, file, cb) => {
        const allowedTypes = /jpeg|jpg|png|pdf|webp/;
        const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
        const mimetype = allowedTypes.test(file.mimetype);

        if (mimetype && extname) {
            return cb(null, true);
        } else {
            cb(new Error('Only PDF and image files (JPEG, PNG, WEBP) are allowed'));
        }
    }
});

// Flask API URL
const FLASK_API_URL = process.env.FLASK_API_URL || 'http://127.0.0.1:5000';

// Routes

/**
 * Health check endpoint
 */
app.get('/health', async (req, res) => {
    try {
        // Check Flask API
        const flaskResponse = await axios.get(`${FLASK_API_URL}/health`, {
            timeout: 5000
        });

        res.json({
            status: 'healthy',
            node: 'running',
            flask: flaskResponse.data.status,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(503).json({
            status: 'degraded',
            node: 'running',
            flask: 'unavailable',
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
});

/**
 * Upload and verify documents
 */
app.post('/upload', upload.array('files', 10), async (req, res) => {
    try {
        if (!req.files || req.files.length === 0) {
            return res.status(400).json({
                error: 'No files uploaded',
                message: 'Please select at least one file to upload'
            });
        }

        console.log(`Received ${req.files.length} files for verification`);

        // Create FormData for Flask API
        const formData = new FormData();
        
        // Add all files to FormData
        for (const file of req.files) {
            formData.append('files', fs.createReadStream(file.path), {
                filename: file.originalname,
                contentType: file.mimetype
            });
        }

        // Send to Flask API
        console.log('Forwarding to Flask API for verification...');
        const flaskResponse = await axios.post(
            `${FLASK_API_URL}/verify`,
            formData,
            {
                headers: {
                    ...formData.getHeaders()
                },
                maxContentLength: Infinity,
                maxBodyLength: Infinity,
                timeout: 120000 // 2 minutes timeout
            }
        );

        // Clean up uploaded files
        for (const file of req.files) {
            try {
                fs.unlinkSync(file.path);
            } catch (err) {
                console.error(`Failed to delete file ${file.path}:`, err);
            }
        }

        // Return verification results
        res.json(flaskResponse.data);

    } catch (error) {
        console.error('Upload error:', error.message);

        // Clean up files on error
        if (req.files) {
            for (const file of req.files) {
                try {
                    fs.unlinkSync(file.path);
                } catch (err) {
                    // Ignore cleanup errors
                }
            }
        }

        // Handle different error types
        if (error.response) {
            // Flask API returned an error
            res.status(error.response.status).json(error.response.data);
        } else if (error.code === 'ECONNREFUSED') {
            res.status(503).json({
                error: 'Service unavailable',
                message: 'Flask API is not available. Please ensure it is running on port 5000.'
            });
        } else {
            res.status(500).json({
                error: 'Internal server error',
                message: error.message
            });
        }
    }
});

/**
 * Get verification by ID
 */
app.get('/verification/:id', async (req, res) => {
    try {
        const response = await axios.get(
            `${FLASK_API_URL}/verification/${req.params.id}`,
            { timeout: 10000 }
        );
        res.json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({
                error: 'Internal server error',
                message: error.message
            });
        }
    }
});

/**
 * List all verifications
 */
app.get('/verifications', async (req, res) => {
    try {
        const { page = 1, limit = 10 } = req.query;
        
        const response = await axios.get(
            `${FLASK_API_URL}/verifications`,
            {
                params: { page, limit },
                timeout: 10000
            }
        );
        
        res.json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({
                error: 'Internal server error',
                message: error.message
            });
        }
    }
});

// Error handling middleware
app.use((error, req, res, next) => {
    console.error('Server error:', error);
    
    if (error instanceof multer.MulterError) {
        if (error.code === 'LIMIT_FILE_SIZE') {
            return res.status(400).json({
                error: 'File too large',
                message: 'File size cannot exceed 50MB'
            });
        }
        return res.status(400).json({
            error: 'Upload error',
            message: error.message
        });
    }
    
    res.status(500).json({
        error: 'Internal server error',
        message: error.message
    });
});

// Start server
app.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log('Medical Document Verification - Node.js Backend');
    console.log('='.repeat(60));
    console.log(`Server running on http://localhost:${PORT}`);
    console.log(`Flask API: ${FLASK_API_URL}`);
    console.log(`Upload directory: ${path.resolve('./uploads')}`);
    console.log('='.repeat(60));
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down gracefully');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('\nSIGINT received, shutting down gracefully');
    process.exit(0);
});
