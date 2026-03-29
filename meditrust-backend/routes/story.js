const express = require('express');
const router = express.Router();
const prisma = require('../utils/prisma');
const { verifyToken } = require('../middleware/auth');
const axios = require('axios');

// ─────────────────────────────────────────
// HELPER — Call Gemini via Vertex AI
// Supports both JSON key and service account authentication
// ─────────────────────────────────────────
const callGemini = async (prompt) => {
  try {
    // Check for Google Cloud configuration
    const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID;
    const jsonKey = process.env.GOOGLE_APPLICATION_CREDENTIALS_JSON;
    const keyFile = process.env.GOOGLE_APPLICATION_CREDENTIALS;

    if (!projectId) {
      console.log('❌ Google Cloud Project ID not configured');
      return {
        success: false,
        gemini_story: null,
        error: 'Google Cloud Project ID not configured'
      };
    }

    // Determine authentication method
    let authConfig = { project: projectId };
    
    if (jsonKey) {
      // JSON key authentication
      try {
        const credentials = JSON.parse(jsonKey);
        authConfig.credentials = credentials;
        console.log('✅ Using JSON key authentication for Gemini');
      } catch (e) {
        console.log('❌ Invalid JSON key format:', e.message);
        return {
          success: false,
          gemini_story: null,
          error: 'Invalid JSON key format in GOOGLE_APPLICATION_CREDENTIALS_JSON'
        };
      }
    } else if (keyFile) {
      // Service account file authentication
      authConfig.keyFile = keyFile;
      console.log('✅ Using service account file authentication for Gemini');
    } else {
      // Default authentication (ADC)
      console.log('✅ Using Application Default Credentials for Gemini');
    }

    // Initialize Vertex AI
    const { VertexAI } = require('@google-cloud/vertexai');
    const vertexAI = new VertexAI({
      ...authConfig,
      location: process.env.GOOGLE_CLOUD_LOCATION || 'us-central1'
    });

    const model = vertexAI.getGenerativeModel({ model: 'gemini-pro' });

    console.log('🚀 Calling Gemini AI with prompt...');
    const result = await model.generateContent(prompt);
    const response = result.response;
    const text = response.candidates[0].content.parts[0].text;

    console.log('✅ Gemini response received successfully');
    return { success: true, gemini_story: text };

  } catch (err) {
    console.log('❌ Gemini call failed:', err.message);
    console.log('📋 Full error:', err);
    
    return { 
      success: false, 
      gemini_story: null, 
      error: `Gemini API error: ${err.message}` 
    };
  }
};

// ─────────────────────────────────────────
// GENERATE — Patient writes story, Gemini polishes it
// ─────────────────────────────────────────
router.post('/generate', verifyToken, async (req, res) => {
  try {
    const { campaign_id, story_original, language } = req.body;

    if (!campaign_id || !story_original) {
      return res.status(400).json({
        success: false,
        error: 'campaign_id and story_original required'
      });
    }

    const campaign = await prisma.campaign.findUnique({
      where: { id: parseInt(campaign_id) }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    if (!['VERIFIED', 'PENDING'].includes(campaign.status)) {
      return res.status(400).json({
        success: false,
        error: 'Campaign must be verified before writing story'
      });
    }

    // Save original story
    await prisma.campaign.update({
      where: { id: parseInt(campaign_id) },
      data : {
        story_original,
        story_language: language || 'en'
      }
    });

    // Build Gemini prompt
    const prompt = `
You are helping a patient write a medical crowdfunding story.

The patient has written the following story in their own language:
"${story_original}"

Please rewrite this story with the following rules:
1. Keep the same language as the original
2. Preserve all emotions and personal feelings
3. Fix grammar and spelling mistakes
4. Make it clear and easy to understand
5. Keep it honest — do not exaggerate or add false details
6. Keep length similar to original
7. Do not add any fake statistics or numbers not mentioned by patient

Return ONLY the rewritten story, nothing else.
`;

    const geminiResult = await callGemini(prompt);

    if (geminiResult.success && geminiResult.gemini_story) {
      // Save Gemini version
      await prisma.campaign.update({
        where: { id: parseInt(campaign_id) },
        data : { story_gemini: geminiResult.gemini_story }
      });

      res.json({
        success       : true,
        story_original,
        story_gemini  : geminiResult.gemini_story,
        message       : 'Story polished by Gemini. Please review and approve or suggest corrections.'
      });
    } else {
      // Google Cloud not configured yet — return original
      res.json({
        success       : true,
        story_original,
        story_gemini  : null,
        message       : 'Gemini not configured yet. You can approve your original story directly.',
        note          : geminiResult.error
      });
    }

  } catch (error) {
    console.error('Story generate error:', error);
    res.status(500).json({ success: false, error: 'Failed to generate story' });
  }
});

// ─────────────────────────────────────────
// CORRECT — Patient suggests corrections, Gemini fixes again
// ─────────────────────────────────────────
router.post('/correct', verifyToken, async (req, res) => {
  try {
    const { campaign_id, corrections } = req.body;

    if (!campaign_id || !corrections) {
      return res.status(400).json({
        success: false,
        error: 'campaign_id and corrections required'
      });
    }

    const campaign = await prisma.campaign.findUnique({
      where: { id: parseInt(campaign_id) }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    if (!campaign.story_gemini) {
      return res.status(400).json({
        success: false,
        error: 'No Gemini story found. Please generate story first.'
      });
    }

    // Build correction prompt
    const prompt = `
You previously wrote this medical crowdfunding story:
"${campaign.story_gemini}"

The patient has the following corrections:
"${corrections}"

Please apply these corrections and rewrite the story.
Keep the same language, preserve emotions, fix only what the patient requested.

Return ONLY the corrected story, nothing else.
`;

    const geminiResult = await callGemini(prompt);

    if (geminiResult.success && geminiResult.gemini_story) {
      await prisma.campaign.update({
        where: { id: parseInt(campaign_id) },
        data : { story_gemini: geminiResult.gemini_story }
      });

      res.json({
        success     : true,
        story_gemini: geminiResult.gemini_story,
        message     : 'Story corrected. Please review and approve.'
      });
    } else {
      res.json({
        success     : true,
        story_gemini: campaign.story_gemini,
        message     : 'Gemini not configured yet. Current story returned.',
        note        : geminiResult.error
      });
    }

  } catch (error) {
    console.error('Story correct error:', error);
    res.status(500).json({ success: false, error: 'Failed to correct story' });
  }
});

// ─────────────────────────────────────────
// APPROVE — Patient approves final story
// ─────────────────────────────────────────
router.post('/approve', verifyToken, async (req, res) => {
  try {
    const { campaign_id, use_original } = req.body;

    if (!campaign_id) {
      return res.status(400).json({
        success: false,
        error: 'campaign_id required'
      });
    }

    const campaign = await prisma.campaign.findUnique({
      where: { id: parseInt(campaign_id) }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    if (!campaign.story_original) {
      return res.status(400).json({
        success: false,
        error: 'No story found. Please write story first.'
      });
    }

    // If patient chooses to use original (when Gemini not available)
    if (use_original) {
      await prisma.campaign.update({
        where: { id: parseInt(campaign_id) },
        data : {
          story_gemini  : campaign.story_original,
          story_approved: true
        }
      });
    } else {
      if (!campaign.story_gemini) {
        return res.status(400).json({
          success: false,
          error: 'No Gemini story to approve. Use use_original: true to approve your original story.'
        });
      }

      await prisma.campaign.update({
        where: { id: parseInt(campaign_id) },
        data : { story_approved: true }
      });
    }

    res.json({
      success: true,
      message: 'Story approved! You can now go live.',
      next   : `POST /api/campaigns/${campaign_id}/go-live`
    });

  } catch (error) {
    console.error('Story approve error:', error);
    res.status(500).json({ success: false, error: 'Failed to approve story' });
  }
});

// ─────────────────────────────────────────
// GET STORY — View current story state
// ─────────────────────────────────────────
router.get('/:campaign_id', verifyToken, async (req, res) => {
  try {
    const campaign = await prisma.campaign.findUnique({
      where : { id: parseInt(req.params.campaign_id) },
      select: {
        id            : true,
        patient_id    : true,
        title         : true,
        story_original: true,
        story_gemini  : true,
        story_language: true,
        story_approved: true,
        status        : true
      }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    res.json({ success: true, story: campaign });

  } catch (error) {
    console.error('Get story error:', error);
    res.status(500).json({ success: false, error: 'Failed to get story' });
  }
});

module.exports = router;