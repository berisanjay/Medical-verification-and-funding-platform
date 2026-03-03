"""
View MongoDB Data Script
Run this to see all your registered users and their data
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import json
from datetime import datetime

def main():
    """Connect to MongoDB and display user data"""
    
    # Load environment variables
    load_dotenv()
    
    # MongoDB connection
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DB_NAME = os.getenv('DB_NAME', 'medical_crowdfunding')
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        print(f"🔗 Connected to MongoDB: {DB_NAME}")
        print(f"🌐 MongoDB URI: {MONGO_URI}")
        print("=" * 50)
        
        # Get all users
        users_collection = db.users
        users = list(users_collection.find({}))
        
        print(f"👥 Total Registered Users: {len(users)}")
        print("=" * 50)
        
        # Display each user
        for i, user in enumerate(users, 1):
            print(f"\n👤 User #{i}")
            print(f"📧 Email: {user.get('email', 'N/A')}")
            print(f"👤 Name: {user.get('profile', {}).get('name', 'N/A')}")
            print(f"🏷 Type: {user.get('user_type', 'N/A')}")
            print(f"📅 Registered: {user.get('created_at', 'N/A')}")
            print(f"✅ Active: {user.get('is_active', 'N/A')}")
            print("-" * 30)
        
        # Get all campaigns
        campaigns_collection = db.campaigns
        campaigns = list(campaigns_collection.find({}))
        
        print(f"\n🏥 Total Campaigns: {len(campaigns)}")
        print("=" * 50)
        
        # Display each campaign
        for i, campaign in enumerate(campaigns, 1):
            print(f"\n💰 Campaign #{i}")
            print(f"📋 Title: {campaign.get('title', 'N/A')}")
            print(f"🏥 Condition: {campaign.get('medical_condition', 'N/A')}")
            print(f"💵 Goal: ${campaign.get('target_amount', 0):,.2f}")
            print(f"💰 Raised: ${campaign.get('current_amount', 0):,.2f}")
            print(f"📊 Status: {campaign.get('status', 'N/A')}")
            print(f"🚨 Urgency: {campaign.get('urgency_level', 'N/A')}")
            print("-" * 30)
        
        # Get all donations
        donations_collection = db.donations
        donations = list(donations_collection.find({}))
        
        print(f"\n💳 Total Donations: {len(donations)}")
        print("=" * 50)
        
        # Display recent donations
        for i, donation in enumerate(donations[-5:], 1):  # Last 5 donations
            print(f"\n💸 Donation #{i}")
            print(f"💰 Amount: ${donation.get('amount', 0):,.2f}")
            print(f"👤 Donor: {donation.get('donor_id', 'N/A')}")
            print(f"🏥 Campaign: {donation.get('campaign_id', 'N/A')}")
            print(f"📅 Date: {donation.get('created_at', 'N/A')}")
            print(f"🕵 Status: {donation.get('status', 'N/A')}")
            print("-" * 30)
        
        print(f"\n📊 Summary:")
        print(f"   Users: {len(users)}")
        print(f"   Campaigns: {len(campaigns)}")
        print(f"   Donations: {len(donations)}")
        print("=" * 50)
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
