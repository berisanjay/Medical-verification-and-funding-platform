const express = require('express');
const router = express.Router();
const axios = require('axios');
const prisma = require('../utils/prisma');

// ─────────────────────────────────────────
// VERIFY PLACE USING GOOGLE PLACES API
// ─────────────────────────────────────────
router.post('/verify-place', async (req, res) => {
  try {
    const { place_name, city, state } = req.body;
    
    if (!place_name || !city) {
      return res.status(400).json({
        success: false,
        error: 'place_name and city are required'
      });
    }

    const apiKey = process.env.GOOGLE_PLACES_API_KEY;
    if (!apiKey) {
      console.log('❌ Google Places API key not configured');
      return res.json({
        success: false,
        verified: false,
        error: 'Google Places API not configured'
      });
    }

    // Search for the place using Google Places API
    const searchQuery = `${place_name}, ${city}, ${state || ''}`;
    const placesUrl = `https://maps.googleapis.com/maps/api/place/textsearch/json?query=${encodeURIComponent(searchQuery)}&key=${apiKey}`;
    
    console.log(`🔍 Searching for place: ${searchQuery}`);
    
    const response = await axios.get(placesUrl);
    const places = response.data;
    
    if (places.status === 'OK' && places.results.length > 0) {
      const place = places.results[0];
      
      // Check if it's a hospital/medical facility
      const isMedical = place.types.some(type => 
        type.includes('hospital') || 
        type.includes('health') || 
        type.includes('doctor') || 
        type.includes('medical') ||
        type.includes('clinic')
      );
      
      console.log(`✅ Place found: ${place.name} (Rating: ${place.rating || 'N/A'})`);
      
      return res.json({
        success: true,
        verified: true,
        place: {
          name: place.name,
          address: place.formatted_address,
          rating: place.rating,
          types: place.types,
          is_medical: isMedical,
          google_place_id: place.place_id
        }
      });
    } else {
      console.log(`❌ Place not found: ${searchQuery}`);
      return res.json({
        success: true,
        verified: false,
        error: 'Place not found in Google Places'
      });
    }
    
  } catch (error) {
    console.error('Place verification error:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to verify place'
    });
  }
});

// ─────────────────────────────────────────
// CREATE SUGGESTION WITH PLACE VERIFICATION
// ─────────────────────────────────────────
router.post('/create', async (req, res) => {
  try {
    const { 
      campaign_id, 
      hospital_name, 
      city, 
      state, 
      disease, 
      treatment_cost, 
      contact_info,
      suggested_by 
    } = req.body;

    if (!hospital_name || !city || !disease) {
      return res.status(400).json({
        success: false,
        error: 'hospital_name, city, and disease are required'
      });
    }

    // First verify the place using Google Places API
    const verifyResponse = await axios.post('http://localhost:3000/api/suggestions/verify-place', {
      place_name: hospital_name,
      city: city,
      state: state
    });

    const google_places_verified = verifyResponse.data.verified;
    let place_details = null;

    if (google_places_verified && verifyResponse.data.place) {
      place_details = {
        google_place_name: verifyResponse.data.place.name,
        google_address: verifyResponse.data.place.address,
        google_rating: verifyResponse.data.place.rating,
        google_place_id: verifyResponse.data.place.google_place_id,
        is_medical_facility: verifyResponse.data.place.is_medical
      };
    }

    // Create suggestion with verification status
    const suggestion = await prisma.suggestion.create({
      data: {
        campaign_id: parseInt(campaign_id),
        hospital_name,
        city,
        state: state || '',
        disease,
        treatment_cost: parseFloat(treatment_cost) || 0,
        contact_info: contact_info || '',
        suggested_by: suggested_by || 'Anonymous',
        google_places_verified,
        ...place_details
      }
    });

    console.log(`✅ Suggestion created: ${hospital_name} (Verified: ${google_places_verified})`);

    res.json({
      success: true,
      suggestion,
      message: google_places_verified 
        ? 'Suggestion created with verified place' 
        : 'Suggestion created (place not verified)'
    });

  } catch (error) {
    console.error('Create suggestion error:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to create suggestion'
    });
  }
});

module.exports = router;
