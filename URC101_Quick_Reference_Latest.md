# URC 101 - Quick Reference Guide
## Version 3.3 - December 2025 - Keep At Your Workstation!

---

## 7 Tabs - Left to Right

1. **Daily Upload Dashboard** (Blue) - Overview + Daily upload
2. **Daily Sales Report** (Green) - Financial reports  
3. **Detailed Analytics** (Purple) - 4 sub-sections of insights
4. **Forecast** (Orange) - Predict future sales
5. **Bulk Data Upload** (Green) - Upload monthly/yearly files
6. **Upload History** (Indigo) - Manage uploads
7. **Database View** (Cyan) - Search, filter, export all data

---

## Tab 1: Daily Upload Dashboard

**Use for**: Daily business monitoring

**Key Features**:
* **Upload Today's Data** button - Quick daily upload
* **Daily Sales Trend** - 3-month line chart
* **Group Performance** - Blue (revenue) + Green (profit) bars
* **Top Sellers** - Metric switcher (Qty/Revenue/**Profit**)
* **Inventory Alerts** - 🔴 Dead | 🟠 Slow | 🟡 High Cost Poor

**Daily Action**: Check trends, verify alerts, upload today's sales

---

## Tab 2: Daily Sales Report

**Use for**: Generate financial reports with auto-calculations

**How to Generate**:
1. Click green "Generate Daily Report" button
2. Enter: Liquor sales (manual)
3. Auto-filled: Grocery sales, Previous balances
4. Leave blank: Current Stock (auto-calculates)
5. Click "Generate & Download PDF"

**Result**: Dashboard updates with new stock value automatically

**Manage Reports**:
* ✏️ Edit button - Modify values
* 🗑️ Delete button - Remove report

---

## Tab 3: Detailed Analytics

**Use for**: Deep business insights (4 sub-sections)

### Filters (Apply to All 4 Sub-Sections)
* **Group Filter**: All Groups or specific category
* **Period Filter**: Current Period, Nov 2025, Jan-Sep 2025, 2024, etc.

### A. Performance Analysis
* **Metric Switcher**: Quantity (Blue) | Revenue (Green) | **Profit** (Orange)
* **3 Charts**: Primary + 2 relationship charts
* **3 Tables**: Ranked by each metric
* **Key Insight**: #1 in sales ≠ #1 in profit!

### B. ABC Analysis
* **Category A** (Green): Top 20% = 80% revenue → Stock generously
* **Category B** (Blue): Next 30% = 15% revenue → Adequate stock
* **Category C** (Red): Bottom 50% = 5% revenue → Minimize/remove

### C. Capital Blocking
* **CRITICAL** (Red): > ₹50K blocked, > 1 year → Urgent clearance!
* **HIGH** (Orange): > ₹10K blocked, > 6 months → Sale within 30 days
* **MEDIUM** (Yellow): > ₹5K blocked, > 3 months → Monitor closely
* **LOW** (Gray): < ₹5K → Normal monitoring

### D. Inventory Health
* **Dead** (Red): Zero sales + have stock → Clear at ANY price
* **Slow** (Orange): < 5 units/month → Stop reordering
* **High Cost Poor** (Yellow): Expensive + not selling → Replace item

**All sections have Export buttons!**

---

## Tab 4: Forecast

**Use for**: Predict future sales, plan inventory

**Methods**:
1. Trend-Based (6+ months data)
2. Statistical (12+ months data)
3. AI-Powered (3+ months data)

**Shows**:
* Predicted quantity
* Confidence level (High/Med/Low)
* Recommended order quantity
* Stock status

**Use forecasts for**: Ordering, promotions, staffing

---

## Tab 5: Bulk Data Upload

**Use for**: Upload monthly, yearly, or multi-month data

### Smart Period Detection (Auto-Detects From Filename!)

**Supported Formats**:
* `"Jan to Sep 2025.xlsx"` → **Jan-Sep 2025** (9 months)
* `"Nov 2025.xlsx"` → **Nov 2025** (1 month)
* `"01 to 30 Oct 25.xlsx"` → **Oct 2025** (1 month)
* `"YR 2024.xlsx"` → **2024** (full year)

**How It Works**:
1. Name file clearly with dates
2. Upload via this tab
3. System detects period from filename
4. Stores correctly in database
5. Shows formatted everywhere: "Jan-Sep 2025"

**Required Columns**:
* Item_Name, Qty, R_Amt, W_Amt (minimum)
* Recommended: GP_Index_No, Product_Group, Rates, Stock

**Steps**:
1. Choose Excel file
2. System validates + detects period
3. Review summary (record count, period)
4. Click "Confirm Upload"
5. Success! Period appears in all dropdowns

---

## Tab 6: Upload History

**Use for**: Track and manage all uploads

**Table Shows**:
* Upload date & time
* Filename
* **Period** (formatted: "Jan-Sep 2025", "Nov 2025")
* Records count
* Status (✅ Success | ❌ Failed)
* **UNDO button** (red)

### UNDO Feature
**When**: Wrong file, duplicate, need to replace
**How**: Click red UNDO → Confirm → Data removed
**Warning**: Cannot be reversed!
**After**: Re-upload corrected file

---

## Tab 7: Database View

**Use for**: Search, filter, export all records

### ⚡ One-Time Migration (Yellow Box at Top)
* **What**: Fixes old period formats
* **When**: After deploying update (only once!)
* **How**: Click "Run Migration" → Confirm → Done
* **Result**: Periods now consistent everywhere

### View Modes
* **Regular**: Individual transactions, actual rates
* **Aggregated** (toggle): Totals per item, **latest rates**

### Filters
* **Group**: All or specific
* **Period**: Current Period, Nov 2025, Jan-Sep 2025, etc.
* **Search**: Type item name
* **GP Index No**: Specific item code

### Export (Works for Large Datasets!)
* Click "Export" button
* Shows progress: "Fetching records... 500/8,894"
* Handles 20K+ records automatically
* Downloads complete CSV with ALL data

**Latest rates in aggregated export** (not averages!)

---

## Report Generation (Top-Right Buttons)

**Two Buttons**: 🟢 Excel Report | 🔵 PDF Report

### Multi-Select Period Feature
1. Click Excel or PDF button
2. Dialog opens with checkboxes
3. **All periods pre-selected** by default
4. Check/uncheck specific periods you want
5. Use "Select All / Deselect All" toggle
6. Counter shows: "X periods selected"
7. Click "Generate Report"

**Period Examples**:
* Single: "Report - Nov 2025"
* Multiple: "Report - Nov 2025 & 2024"
* Range: "Report - Jan-Sep 2025 to 2022 (4 periods)"

**Validation**: Must select at least one period!

---

## 7-Sheet Excel Report Contents

1. **Executive Summary** - Key metrics, period in title
2. **ABC Analysis** - A/B/C classification
3. **Capital Blocking** - Top 50 problem items
4. **Group Performance** - Category breakdown (Group VI, III, etc.)
5. **Top Performers** - Best 20 items with groups
6. **Items to Liquidate** - Bottom 20 to clear
7. **Smart Recommendations** - Actionable strategies

**PDF Report**: Same content, professional format

---

## Period Formats (Consistent Everywhere!)

**What You'll See**:
* **Current Period (Dec 2025)** - This month
* **Nov 2025** - Complete month
* **Jan-Sep 2025** - Multi-month range (9 months)
* **2024** - Full year

**Where Consistent**:
* Dashboard period selector
* Analytics dropdown
* Report generation modal
* Database View filter
* Upload History table

---

## Daily Routine for Clerk (15 minutes)

### Morning (5 min)
* Check Dashboard
* Verify yesterday's upload successful
* Note any alerts

### Evening (10 min)
1. Upload today's sales (Dashboard or Daily Sales Report tab)
2. Generate financial report if required
   * Enter liquor sales
   * Leave stock blank (auto-calculates)
   * Download PDF
3. Verify Dashboard updated

---

## Weekly Routine for Manager (30 minutes)

### Monday Morning
1. **Analytics Review** (15 min)
   * Tab 3: Detailed Analytics
   * Select "Current Period"
   * Check all 4 sub-sections
   * Note CRITICAL capital blocking items

2. **Plan Clearances** (10 min)
   * Focus on red/orange alerts
   * Set weekly targets
   * Assign actions

3. **Export Weekly Data** (5 min)
   * Database View → Export
   * Review offline

### Friday
* Generate report for current month
* Brief team on next week priorities

---

## Monthly Routine for Management (2-3 hours)

### First Week of New Month
1. **Upload Complete Month**
   * Name file: "Nov 2025.xlsx"
   * Bulk Data Upload tab
   * Verify period detected correctly

2. **Generate Multi-Period Report**
   * Select last 3 months
   * Excel + PDF
   * Review all 7 sheets
   * Focus on Sheet 7 (Recommendations)

3. **Strategic Decisions**
   * ABC Analysis: Adjust stocking
   * Capital Blocking: Plan clearances
   * Set monthly targets

4. **Team Communication**
   * Share relevant sheets
   * Assign action items
   * Schedule follow-up

---

## Quick Actions Checklist

### After Deployment (One-Time)
- [ ] Go to Database View tab
- [ ] Click "Run Migration" (yellow box)
- [ ] Confirm migration
- [ ] Verify periods now formatted everywhere
- [ ] Test report generation

### Daily
- [ ] Upload today's sales (proper filename)
- [ ] Generate financial report (if required)
- [ ] Check Dashboard for alerts
- [ ] Verify upload successful

### Weekly
- [ ] Review Analytics (all 4 sub-sections)
- [ ] Check capital blocking (CRITICAL items)
- [ ] Plan clearances
- [ ] Export data for records

### Monthly
- [ ] Upload complete month (named: "Month Year.xlsx")
- [ ] Generate 3-month report
- [ ] Review all 7 sheets
- [ ] Implement recommendations
- [ ] Set new targets

---

## Common Errors - Quick Fixes

| Problem | Solution |
|---------|----------|
| Periods don't match | Run migration in Database View |
| Export has zero rates | Update to latest, latest rates now included |
| Export fails (many records) | Latest version uses chunked export, works now |
| Analytics shows no data | Check period filter, run migration |
| Period not detected | Name file clearly: "Jan to Sep 2025.xlsx" |
| "Data already exists" | UNDO old upload, then re-upload |
| Group shows "NA" | Update to v3.3, groups now fixed |
| No periods to select | Upload data first via Bulk Data Upload |

---

## Key Numbers to Remember

**Good Profit Margin**: > 20% (Green)
**Okay**: 10-20% (Orange)
**Poor**: < 10% (Red)

**Slow Moving**: < 5 units/month
**Dead Inventory**: 0 sales + stock > 0

**Capital Blocking**:
* CRITICAL: > ₹50,000
* HIGH: > ₹10,000
* MEDIUM: > ₹5,000

**ABC Rule**: Top 20% items = 80% revenue

---

## Color Codes Reference

**Blue**: Quantity metrics, Dashboard tab
**Green**: Revenue metrics, upload tabs, financial
**Orange**: Profit metrics, forecast tab
**Purple**: Analytics tab
**Indigo**: History tab
**Cyan**: Database tab

**Red**: Critical alerts, dead inventory
**Orange**: High alerts, slow moving
**Yellow**: Medium alerts, warnings, migration box
**Gray**: Low priority, normal monitoring

---

## Pro Tips (v3.3)

✅ **Name files clearly**: "Jan to Sep 2025.xlsx" for auto-detection
✅ **Run migration once**: After deployment for period fixes
✅ **Use aggregated export**: Shows latest rates per item
✅ **Multi-period reports**: Compare trends across time
✅ **Focus on PROFIT view**: Not just quantity!
✅ **Act on CRITICAL**: Capital blocking urgent items first
✅ **Check groups**: Now showing Group VI, III correctly
✅ **Export large datasets**: Chunked export handles 20K+ records
✅ **Period consistency**: Same everywhere now!
✅ **Leave stock blank**: Financial reports auto-calculate

---

## Emergency Actions

**System slow**: Clear cache (Ctrl+Shift+R), restart browser
**Upload fails**: Check filename format, required columns
**Wrong data uploaded**: UNDO immediately in Upload History
**Periods don't match**: Run migration (Database View)
**Export fails**: Update to latest version (chunked export)
**Numbers wrong**: Verify source Excel, check calculations

---

## Version 3.3 Highlights (Latest!)

✅ **Accurate Documentation**: Matches actual code exactly
✅ **Correct Tab Order**: 7 tabs documented left-to-right
✅ **Latest Rates**: Aggregated exports show recent prices
✅ **Chunked Export**: Handles 20K+ records efficiently
✅ **Period Consistency**: Same format everywhere
✅ **Smart Detection**: Auto-recognizes date ranges
✅ **Multi-Period Reports**: Combine any time periods
✅ **Migration Tool**: One-click period format fix
✅ **Group Data**: Shows Group VI, III, etc. correctly
✅ **Auto-Calculations**: Stock values calculated automatically

---

## Tab Navigation Quick Keys (For Desktop)

Not available - use mouse/touch to click tabs

---

## When to Use Each Tab

| Need to... | Use Tab |
|-----------|---------|
| See today's performance | 1. Daily Upload Dashboard |
| Upload daily sales | 1. Dashboard or 2. Daily Sales Report |
| Generate financial report | 2. Daily Sales Report |
| Edit/delete financial report | 2. Daily Sales Report |
| See best/worst sellers | 3. Detailed Analytics → Performance |
| Classify inventory (ABC) | 3. Detailed Analytics → ABC Analysis |
| Find problem stock | 3. Detailed Analytics → Capital Blocking |
| Check dead inventory | 3. Detailed Analytics → Inventory Health |
| Predict future sales | 4. Forecast |
| Upload monthly/yearly data | 5. Bulk Data Upload |
| Verify uploads | 6. Upload History |
| Remove wrong upload | 6. Upload History (UNDO) |
| Search specific item | 7. Database View |
| Export all data | 7. Database View |
| Fix period formats | 7. Database View (Migration) |
| Generate comprehensive report | Any tab (top-right buttons) |

---

## File Naming Best Practices

**Good Examples** ✅:
* `"Jan to Sep 2025.xlsx"` - Multi-month range
* `"Nov 2025.xlsx"` - Single month
* `"November 2025.xlsx"` - Also works
* `"01 to 30 Oct 25.xlsx"` - With dates
* `"YR 2024.xlsx"` - Full year
* `"2024.xlsx"` - Year simple

**Bad Examples** ❌:
* `"grocery_sales.xlsx"` - No period info
* `"final_report.xlsx"` - No dates
* `"data.xlsx"` - Too generic
* `"Nov.xlsx"` - Missing year
* `"11-2025.xlsx"` - Unclear format

---

## Data Quality Checklist

Before uploading:
- [ ] Headers match required columns
- [ ] No "Total" rows at bottom
- [ ] No summary/formula rows
- [ ] Numbers are values, not formulas
- [ ] No currency symbols in cells
- [ ] Item names consistent
- [ ] Group names consistent
- [ ] File named with period info
- [ ] File size under 50MB

---

## Smart Features to Know

**Auto-Calculations**:
* Profit = R_Amt - W_Amt
* Margin = (Profit / Revenue) × 100
* Stock Value = Latest_Rate × Closing_Stock

**Auto-Population**:
* Grocery Sales (from daily upload)
* Previous balances (from yesterday's report)
* Period detection (from filename)
* Latest rates (for aggregated view)

**Auto-Updates**:
* Dashboard after financial report
* All tabs after new upload
* Period dropdowns after upload
* Charts and tables real-time

---

## Success Metrics to Track

**Daily**:
* Upload completion rate (should be 100%)
* Alert count (decreasing = good)
* Top seller changes

**Weekly**:
* Dead inventory count (↓ is good)
* CRITICAL capital blocking (↓ is good)
* Clearance progress (items removed)

**Monthly**:
* Profit margin trend (↑ is good)
* Category C item count (↓ is good)
* Total capital blocked (↓ is good)
* Revenue per square foot (↑ is good)

---

**Keep this guide visible at your workstation!**

**Quick Questions?** Check the full User Handbook for detailed explanations.

**Need Help?** Contact your system administrator.

**Version 3.3** | December 2025 | URC 101 Grocery Sales Analytics

**Latest Features**: Smart period detection, multi-period reports, latest rates, chunked exports, period consistency, migration tool
