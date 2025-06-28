import streamlit as st
from datetime import datetime, timedelta
import json
import os

class UsageLimiter:
    def __init__(self, daily_limit=100, monthly_limit=1000):
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.usage_file = "usage_tracking.json"
    
    def get_usage_data(self):
        """Get current usage data"""
        if 'usage_data' not in st.session_state:
            st.session_state.usage_data = {
                'daily_count': 0,
                'monthly_count': 0,
                'last_reset_day': datetime.now().strftime('%Y-%m-%d'),
                'last_reset_month': datetime.now().strftime('%Y-%m')
            }
        return st.session_state.usage_data
    
    def reset_counters_if_needed(self, usage_data):
        """Reset counters if day/month has changed"""
        today = datetime.now().strftime('%Y-%m-%d')
        this_month = datetime.now().strftime('%Y-%m')
        
        if usage_data['last_reset_day'] != today:
            usage_data['daily_count'] = 0
            usage_data['last_reset_day'] = today
        
        if usage_data['last_reset_month'] != this_month:
            usage_data['monthly_count'] = 0
            usage_data['last_reset_month'] = this_month
    
    def can_translate(self):
        """Check if translation is allowed"""
        usage_data = self.get_usage_data()
        self.reset_counters_if_needed(usage_data)
        
        if usage_data['daily_count'] >= self.daily_limit:
            return False, f"Daily limit reached ({self.daily_limit} translations)"
        
        if usage_data['monthly_count'] >= self.monthly_limit:
            return False, f"Monthly limit reached ({self.monthly_limit} translations)"
        
        return True, "OK"
    
    def increment_usage(self):
        """Increment usage counters"""
        usage_data = self.get_usage_data()
        usage_data['daily_count'] += 1
        usage_data['monthly_count'] += 1
        st.session_state.usage_data = usage_data
    
    def show_usage_stats(self):
        """Display current usage statistics"""
        usage_data = self.get_usage_data()
        self.reset_counters_if_needed(usage_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Daily Usage", f"{usage_data['daily_count']}/{self.daily_limit}")
        with col2:
            st.metric("Monthly Usage", f"{usage_data['monthly_count']}/{self.monthly_limit}")
