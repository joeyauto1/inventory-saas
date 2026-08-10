# Square App Marketplace — App Review Guide

> This document is what Square reviewers will use to test the app.
> Keep it clear, step-by-step, and assume they're a real restaurant owner.

## TEST CREDENTIALS
- **Square Sandbox Account:** [PROVIDE]
- **Test App Login:** [PROVIDE]
- **Stripe Test Card:** 4242 4242 4242 4242, any future expiry, any CVC

## HOW TO TEST

### Step 1: Connect Your Square Account
1. Go to [APP_URL]
2. Click "Connect Your Square Account"
3. You'll be redirected to Square's OAuth page
4. Sign in with the test Square account
5. Authorize the requested permissions (Inventory Read, Items Read, Orders Read, Merchant Profile Read)
6. You'll be redirected to the dashboard

### Step 2: Sync Inventory
1. From the sidebar, click "Inventory"
2. Click "Sync from Square"
3. Your Square catalog items and current inventory levels will appear in a table
4. Items show stock levels with color-coded status: green (OK), amber (low), red (out)

### Step 3: Log Waste
1. From the sidebar, click "Waste"
2. Fill in the waste log form:
   - Item name: "Chicken Breast"
   - Quantity: 2.5
   - Reason: "spoilage"
   - Cost per unit: 8.50
3. Click "Log Waste"
4. The waste event appears in the log table below with calculated cost ($21.25)
5. Click "Load" to refresh the waste log

### Step 4: Build a Recipe
1. From the sidebar, click "Recipes"
2. Create a recipe:
   - Name: "Chicken Parmigiana"
   - Sell Price: 24.00
   - Portions: 1
3. Click the recipe card to open detail view
4. Add ingredients:
   - Item name: "Chicken Breast", Qty: 200, Unit: g, Cost: 0.0425/g
   - Item name: "Tomato Sauce", Qty: 100, Unit: ml, Cost: 0.006/ml
   - Item name: "Mozzarella", Qty: 50, Unit: g, Cost: 0.018/g
5. View the calculated cost per portion and margin

### Step 5: Run a Report
1. From the sidebar, click "Reports"
2. Select "Last 30 days"
3. Click "Run Report"
4. View: total waste cost, breakdown by reason, top 10 wasted items

### Step 6: Manage Subscription
1. From the sidebar, click "Settings"
2. View subscription status (trial active)
3. Click "Manage in Stripe" to access billing portal

## WHAT TO VERIFY
- [ ] OAuth flow completes successfully
- [ ] Inventory syncs from Square catalog
- [ ] Waste events log and display correctly
- [ ] Recipe costing calculates correctly
- [ ] Reports aggregate correctly
- [ ] Subscription status displays correctly
- [ ] Disconnect Square works
- [ ] All pages load without errors
- [ ] No sensitive data exposed in browser console or network requests

## SECURITY NOTES FOR REVIEWERS
- Square access tokens are AES-256 encrypted with Fernet (symmetric encryption)
- Encryption key is stored as an environment variable, never in source control
- All API communication uses HTTPS
- Webhook endpoints verify HMAC-SHA256 signatures
- OAuth secret is never stored in source control
- Exponential backoff implemented for Square API rate limit handling
