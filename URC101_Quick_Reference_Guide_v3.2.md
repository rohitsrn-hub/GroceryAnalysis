# URC 101 - Quick Reference Guide for Daily Use
**Version 3.2 - Keep this guide handy for quick lookups!**

---

## Daily Upload Dashboard Tab
**Purpose**: Overview of business performance + daily data upload

**What you see**:
* Total revenue, profit, items sold, profit margin
* **Current stock value** (with refresh button 🔄)
* **Daily sales trend** - Line chart for current quarter (3 months)
* Group-wise performance charts
* **Top selling items** - Dynamic selector (Quantity/Revenue/Profit)
  * Color-coded: Blue (Quantity) / Green (Revenue) / Orange (Profit)
* Inventory alerts (dead, slow moving, high cost items)

**Daily action**:
* Check daily sales trend for patterns
* Switch top sellers view (try all 3 metrics!)
* Verify stock value updated (use refresh button if needed)

**NEW Features (v3.2)**:
* **Responsive Layout**: Adapts to screen size automatically
* **Metric Switcher**: Change top sellers view instantly
* **Auto-Update**: Dashboard refreshes after financial report generation

---

## Daily Sales Report Tab
**Purpose**: Generate and manage daily financial reports

**What to enter**:
* Liquor sales (manual entry required)
* Grocery sales (auto-calculated from upload)
* Previous bank/stock (auto-filled from yesterday)
* Current stock (optional - auto-calculated if blank)

**How to generate**:
1. Click "Daily Sales Report" tab
2. Click green "Generate Daily Report" button
3. Enter liquor sales
4. Verify auto-filled values
5. Click "Generate & Download PDF"
6. Dashboard updates automatically

**Edit/Delete Reports**:
* Click blue ✏️ Edit button to modify
* Click red 🗑️ Delete button to remove
* Changes reflect immediately

**When to use**: End of each business day

---

## Detailed Analytics Tab
**Purpose**: Advanced business insights (4 sub-tabs with period filter)

### Period Filter (NEW - v3.2!)
**What you'll see**:
* **Current Period (Dec 2025)** - This month
* **Nov 2025** - Individual months
* **Jan-Sep 2025** - Multi-month ranges  
* **2024, 2023, 2022** - Full years

**Consistent everywhere**: Same periods in Analytics and Report generation!

### 1. Performance Analysis (Enhanced)
**Metric Selector** - Switch views instantly:
* **Quantity Sold** (Blue) - Most popular items
* **Revenue Generated** (Green) - Highest sales
* **Profit Earned** (Orange) - **Most important!**

**3 Interactive Charts**: Primary + 2 relationship charts

**Key insight**: Item can be #1 in sales but #10 in profit!

**Pro tip**: Always check "Profit Earned" view - it's what really matters!

### 2. ABC Analysis
**Categories**:
* **Category A** (Green): Top 20% items = 80% revenue → Stock generously
* **Category B** (Blue): Next 30% items = 15% revenue → Adequate stock
* **Category C** (Red): Bottom 50% items = 5% revenue → Reduce/discontinue

**Use for**: Inventory space allocation and ordering priorities

### 3. Capital Blocking
**Risk levels**:
* **CRITICAL** (Red): > ₹50K blocked, > 1 year to sell → Urgent action!
* **HIGH** (Orange): > ₹10K blocked, > 6 months to sell → Clearance sale
* **MEDIUM** (Yellow): > ₹5K blocked, > 3 months to sell → Monitor closely
* **LOW** (Gray): Lesser amounts → Normal monitoring

**Smart Sorting** (NEW): Items sorted by urgency, not just amount!

**Action**: Clear critical items through sales/returns immediately

### 4. Inventory Health
**Three alerts**:
* **Dead** (Red): Zero sales, have stock → Sell at any price
* **Slow Moving** (Orange): < 5 units/month → Reduce orders
* **High Cost Poor** (Yellow): Expensive + not selling → Replace item

**Weekly action**: Review and take corrective measures

---

## Bulk Data Upload Tab
**Purpose**: Upload monthly/yearly sales files

**Smart Period Detection (NEW - v3.2!)**:
* **"Jan to Sep 2025.xlsx"** → Shows as "Jan-Sep 2025" everywhere
* **"Nov 2025.xlsx"** → Shows as "Nov 2025"
* **"01 to 30 Oct 25.xlsx"** → Shows as "Oct 2025"
* **"YR 2024.xlsx"** → Shows as "2024"

**Best filename formats**:
* Range: "Jan to Sep 2025.xlsx"
* Month: "November 2025.xlsx"
* Year: "2024.xlsx"

**How to upload**:
1. Click "Bulk Data Upload" tab
2. Select your Excel file
3. Wait for validation
4. **Period auto-detected** from filename
5. Click "Confirm Upload"

**Note**: System warns if period already exists

---

## Upload History Tab
**Purpose**: Track all uploads and manage data

**What you see**:
* List of all uploaded files
* Upload date, **formatted period** (e.g., "Jan-Sep 2025"), record count
* Status (Success ✅ or Failed ❌)

**Key feature**: **UNDO button** - removes uploaded data if needed

**Daily action**: Verify today's upload was successful

---

## Database View Tab
**Purpose**: Search records + Admin tools

### ⚡ One-Time Migration (NEW - v3.2!)
**Yellow box at top** - Run once after deployment

**What it does**:
* Fixes old period formats
* Updates "Jan 2025" → "Jan-Sep 2025" for range data
* One-click from mobile or desktop

**How to use**:
1. Click "Database View" tab
2. Find yellow "⚡ One-Time Migration" box
3. Click orange "Run Migration" button
4. Confirm when prompted
5. Wait for success message (shows count updated)

**When to use**:
* After deploying latest update
* If periods show incorrectly
* Only need to run once!

### Database Search
* **Search**: Type item name or code
* **Sort**: Click column headers
* **Export**: Download as Excel/CSV/PDF

---

## Report Generation (Enhanced - v3.2!)
**Multi-Select Period Feature** - Generate reports for any time range!

**How to use**:
1. Click "Excel Report" or "PDF Report" (top-right)
2. Dialog opens with **all periods pre-selected**
3. **Select/deselect** specific periods with checkboxes
4. Use "Select All / Deselect All" toggle
5. See count: "X periods selected"
6. Click "Generate Report"

**Period formats in dialog**:
* **Current Period (Dec 2025)** - This month
* **Nov 2025** - Monthly data
* **Jan-Sep 2025** - Range data
* **2024, 2023, 2022** - Yearly data

**Report title shows**:
* Single: "Report - Nov 2025"
* Multiple: "Report - Nov 2025 & 2024"
* Many: "Report - Nov 2025 to 2022 (5 periods)"

**Validation**: Must select at least one period!

**Use cases**:
* Single month: Detailed monthly analysis
* Quarter: Last 3 months comparison
* Year-over-year: Compare 2024 vs 2023
* Custom: Any period combination

---

## Excel Report (7 Sheets)

1. **Executive Summary** - Key metrics with period in title
2. **ABC Analysis** - Item classification (A/B/C)
3. **Capital Blocking** - Top 50 items blocking money
4. **Group Performance** - Category breakdown (**Group VI, Group III, etc. now shown!**)
5. **Top Performers** - Best 20 items (**with group data!**)
6. **Items to Liquidate** - 20 slowest items to clear
7. **Smart Recommendations** - Action plans with targets

---

## Quick Tips for Clerks

### Morning Routine (5 minutes)
1. Open Dashboard
2. Check yesterday's top sellers
3. Note any inventory alerts
4. Print if needed for manager

### Evening Routine (10 minutes)
1. Upload today's sales file
   * File saved with today's date
   * System auto-detects period
2. Generate financial report
   * Click "Daily Sales Report" tab
   * Enter liquor sales
   * Leave stock blank for auto-calculation
   * Download PDF
3. Verify upload success in Upload History
4. Check dashboard stock value updated (use 🔄 if needed)

### Monthly Routine (15 minutes)
1. Upload complete monthly file
   * Name it properly: "Nov 2025.xlsx"
   * System auto-detects period
2. Verify record count and period format
3. Check for any error messages
4. Inform manager of completion

### After New Deployment (One-time)
1. Go to Database View tab
2. Click "Run Migration" button (yellow box)
3. Confirm and wait
4. Verify periods now show correctly

---

## Common Errors - Quick Fix

| Error | Quick Fix |
|-------|-----------|
| "Data already exists" | Use UNDO on old upload, then re-upload |
| Wrong period format | Name file correctly: "Jan to Sep 2025.xlsx" |
| Periods don't match | Run migration in Database View tab |
| No periods in report | Check at least one period is selected |
| Group shows "NA" | Update to v3.2, regenerate report |
| "No valid records" | Remove total rows and summary from Excel |
| "Failed to load" | Refresh browser (Ctrl+Shift+R) |

---

## Quick Reference - When to Use Each Tab

| Task | Use This Tab |
|------|--------------|
| Daily sales overview | Daily Upload Dashboard |
| Upload monthly/yearly data | Bulk Data Upload |
| Check upload worked | Upload History |
| Find specific item | Database View |
| Fix period formats | Database View → Migration button |
| See best sellers | Dashboard or Detailed Analytics |
| Identify dead stock | Detailed Analytics → Inventory Health |
| Find money locked | Detailed Analytics → Capital Blocking |
| Classify inventory | Detailed Analytics → ABC Analysis |
| Plan future orders | Forecasting |
| Track daily money | Daily Sales Report |
| Edit/delete reports | Daily Sales Report → Actions |
| **Generate multi-period report** | **Top-right Excel/PDF buttons → Select periods** |

---

## Important Numbers to Remember

**Good Profit Margin**: > 20% (Green)
**Okay Profit Margin**: 10-20% (Orange)
**Poor Profit Margin**: < 10% (Red)

**Slow Moving**: < 5 units/month
**Dead Inventory**: 0 sales but in stock

**Capital Blocking Critical**: > ₹50,000
**ABC Rule**: Top 20% items = 80% revenue

---

## Color Codes Quick Reference

**Blues**: Quantity-related metrics
**Greens**: Revenue-related metrics
**Oranges**: Profit-related metrics
**Reds**: Alerts, critical items, problems
**Yellows**: Warnings, caution items, migration box

---

## Pro Tips (Updated for v3.2)

* **Upload regularly**: Don't skip days
* **Name files correctly**: "Jan to Sep 2025.xlsx" for auto-detection
* **Run migration once**: After deployment to fix old periods
* **Check period consistency**: Should match in Analytics & Reports
* **Use multi-period reports**: Compare trends across time
* **Check Group data**: Now shows Group VI, Group III correctly
* **Use Profit view**: More important than Quantity
* **Export reports**: Keep monthly records
* **Focus on ABC-A**: These are your VIPs
* **Clear dead stock**: Don't let it accumulate
* **Don't ignore warnings**: Small problems become big
* **Don't guess**: Use data, not intuition

---

## NEW Features Checklist (v3.2)

**Smart Period Detection**:
- [✓] Upload "Jan to Sep 2025.xlsx" → Shows as "Jan-Sep 2025"
- [✓] Single month files auto-detected
- [✓] Yearly files recognized

**Multi-Select Reports**:
- [✓] Select multiple periods with checkboxes
- [✓] Generate combined analysis
- [✓] Period names in report title

**Period Consistency**:
- [✓] Same format in Analytics dropdown
- [✓] Same format in Report generation
- [✓] Current month auto-detected

**Data Accuracy**:
- [✓] Group data now showing (Group VI, etc.)
- [✓] Migration tool available
- [✓] One-click period format fix

---

## Quick Actions Checklist

**Daily (Clerk)**
- [ ] Upload today's data (proper filename)
- [ ] Generate financial report (auto-calculates stock)
- [ ] Check upload success
- [ ] Verify dashboard updated (use 🔄 if needed)
- [ ] Confirm period shows correctly

**After Deployment (One-Time)**
- [ ] Go to Database View tab
- [ ] Click "Run Migration" button
- [ ] Confirm migration
- [ ] Verify periods now match everywhere
- [ ] Test report generation

**Weekly (Store Manager)**
- [ ] Review Dashboard
- [ ] Check inventory alerts
- [ ] Act on critical capital blocking
- [ ] Export weekly report (select last 7 days if available)
- [ ] Verify group data in reports

**Monthly (Inventory Manager)**
- [ ] Upload monthly file (named properly: "Nov 2025.xlsx")
- [ ] Verify period auto-detected correctly
- [ ] Complete ABC analysis
- [ ] Review dead inventory
- [ ] Generate multi-period report (current + last 3 months)
- [ ] Plan next month's orders

---

## Emergency Actions

* **If system is slow**: Clear browser cache, restart browser
* **If upload fails 3 times**: Check Excel file format, check filename
* **If wrong data uploaded**: Use UNDO immediately
* **If periods don't match**: Run migration in Database View
* **If group shows NA**: Update to v3.2, regenerate reports
* **If numbers look wrong**: Verify source Excel file first

---

## Version 3.2 Highlights

✅ **Smart Period Detection**: Automatically recognizes "Jan to Sep 2025"
✅ **Multi-Select Reports**: Generate reports for any time range
✅ **Period Consistency**: Same format everywhere in the app
✅ **Migration Tool**: One-click fix for old period formats
✅ **Group Data Fixed**: Shows Group VI, Group III correctly
✅ **Updated Tab Names**: Clearer navigation (Daily Upload Dashboard, Bulk Data Upload, etc.)
✅ **Current Month Detection**: Automatically shows "Current Period (Dec 2025)"

---

**Keep this guide at your workstation for quick reference!**

**Remember**: When in doubt, check the full User Handbook or contact your supervisor.

**Version 3.2** | Updated: December 2025 | URC 101 Grocery Sales Analytics

**Latest Features**: Smart period detection, multi-select reports, period consistency, migration tool, group data fixes
