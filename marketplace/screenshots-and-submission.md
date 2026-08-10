# Marketplace Screenshot Requirements

For Square App Marketplace listing, you need 3-5 screenshots plus an app icon.

## APP ICON
- 1024 x 1024 pixels
- PNG format
- Should be recognizable at small sizes (shown at ~80px in search results)
- Design: green/emerald (#059669) background with a clipboard/chart icon in white

## REQUIRED SCREENSHOTS (2880 x 1800px recommended, PNG)

1. **Inventory Dashboard** — Table of items with stock levels, green/amber/red status badges visible
   - Shows the main value: "I can see what's in stock at a glance"

2. **Waste Log Form** — The waste entry form filled out, waste log table below
   - Shows the core feature: logging waste is fast and simple

3. **Recipe Costing** — Recipe detail with ingredients, costs, and margin calculation
   - Shows the money feature: "I know exactly what this dish costs"

4. **Reports Page** — Waste breakdown by reason with percentage bars, top wasted items
   - Shows the insight: "I know where my money is going"

5. **Landing/Connect Page** — The "Connect Your Square Account" page
   - Shows the onboarding: simple, professional, trustworthy

## TO CAPTURE SCREENSHOTS
1. Run the app locally: `cd frontend && npm run dev` and `cd backend && uvicorn app.main:app`
2. Connect a Square sandbox account
3. Load some test catalog items
4. Log several waste events with different reasons
5. Create 2-3 recipes with ingredients
6. Screenshot each page at 2880x1800 (or highest available resolution)

## SQUARE SUBMISSION CHECKLIST

Before submitting to Square:

- [ ] AES-256 encryption of access tokens implemented
- [ ] Exponential backoff on Square API calls
- [ ] OAuth client secret in environment variable, not source control
- [ ] Token encryption key in environment variable, not source control
- [ ] Webhook signature verification enabled
- [ ] HTTPS on production deployment
- [ ] App icon uploaded (1024x1024 PNG)
- [ ] 3-5 screenshots uploaded (2880x1800 PNG)
- [ ] Listing copy entered
- [ ] Onboarding guide URL provided
- [ ] App usage instructions for reviewers provided
- [ ] Privacy policy URL provided
- [ ] Terms of service URL provided
- [ ] Test credentials provided for Square reviewer
- [ ] Stripe test card provided for reviewer

## SUBMISSION FLOW
1. Go to https://developer.squareup.com/apps
2. Select your app
3. Navigate to "App Marketplace" tab
4. Fill in listing details using copy from `square-listing-copy.md`
5. Upload screenshots and icon
6. Provide reviewer guide from `reviewer-guide.md`
7. Submit for review
8. Review time: 1-2 weeks
