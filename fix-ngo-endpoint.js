// ─────────────────────────────────────────
// TOKEN-BASED NGO RESPONSE (from email links)
// POST /api/ngo/respond
// Called when NGO clicks approve/reject in email with token
// ─────────────────────────────────────────
router.post('/respond', async (req, res) => {
  try {
    const { token, status } = req.body; // ACCEPTED or REJECTED

    if (!token) {
      return res.status(400).json({
        success: false,
        error: 'Response token is required'
      });
    }

    if (!['ACCEPTED', 'REJECTED'].includes(status)) {
      return res.status(400).json({
        success: false,
        error: 'Status must be ACCEPTED or REJECTED'
      });
    }

    // Find match by token
    const match = await prisma.nGOMatch.findFirst({
      where: { 
        response_token: token,
        response_expires_at: { gt: new Date() }
      },
      include: { 
        campaign: {
          include: {
            fund_needer: true
          }
        }
      }
    });

    if (!match) {
      return res.status(404).json({ 
        success: false, 
        error: 'Invalid or expired response link' 
      });
    }

    // Update match status
    await prisma.nGOMatch.update({
      where: { id: match.id },
      data: {
        status: status,
        responded_at: new Date(),
        response_token: null, // Invalidate token after use
        response_expires_at: null
      }
    });

    // Notify admin
    await prisma.adminAuditLog.create({
      data: {
        admin_id: 1, // System admin
        action: `NGO_RESPONDED_${status}`,
        target_type: 'ngo_match',
        target_id: match.id,
        notes: `NGO responded ${status} via email link`
      }
    });

    res.json({
      success: true,
      message: status === 'ACCEPTED' 
        ? 'Thank you for accepting! We will coordinate with you for fund disbursement.'
        : 'Response recorded. Thank you for letting us know.',
      match_id: match.id
    });

  } catch (error) {
    console.error('NGO token respond error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Failed to record NGO response' 
    });
  }
});
