from .fulfillment_manager import FulfillmentManager

__all__ = ["FulfillmentManager"]
""" ```

---

### What Changed & Why

| Old Code | New Code |
|---|---|
| MongoDB queries everywhere | Zero DB — talks to Node.js via HTTP |
| Fetched donors/campaigns from Mongo | Node.js passes all data via `/internal/` endpoints |
| No HMS checks | 3 pre-release HMS checks before every payout |
| No document expiry check | Added `_check_expired_documents()` |
| No thread control | Clean `start()` and `stop()` methods |
| Hardcoded Stripe/dollar | Razorpay + Rs. amounts |

---

Also add this to `meditrust-backend/.env`:
```
FLASK_INTERNAL_SECRET=meditrust_flask_internal_2026
```

And add same to `flask-backend/.env`:
 """""" ```
FLASK_INTERNAL_SECRET=meditrust_flask_internal_2026
MEDITRUST_BACKEND_URL=http://localhost:3000
HMS_BASE_URL=http://localhost:4000 """