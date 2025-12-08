# URC 101 Grocery Sales Analytics - User Handbook
## Version 3.2 - Complete Analytics Edition
**For: Store Managers, Inventory Managers, and Staff**

---

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Daily Upload Dashboard Tab](#daily-upload-dashboard-tab)
4. [Bulk Data Upload Tab](#bulk-data-upload-tab)
5. [Upload History Tab](#upload-history-tab)
6. [Database View Tab](#database-view-tab)
7. [Detailed Analytics Tab](#detailed-analytics-tab)
8. [Forecasting Tab](#forecasting-tab)
9. [Daily Sales Report Tab](#daily-sales-report-tab)
10. [Report Generation](#report-generation)
11. [Understanding Your Reports](#understanding-your-reports)
12. [Best Practices](#best-practices)
13. [Troubleshooting](#troubleshooting)

---

# 1. Introduction

### What is URC 101 Grocery Sales Analytics?
URC 101 is a powerful yet easy-to-use application designed to help you manage and analyze your grocery store's sales data. Whether you're tracking daily sales, identifying your best-selling products, or planning your inventory, this app makes it simple.

### Who Should Use This App?
* Store Managers: Get insights into overall business performance
* Inventory Managers: Optimize stock levels and identify slow-moving items
* Data Entry Clerks: Upload daily and monthly sales data
* Business Owners: Make informed decisions based on data

### Key Benefits
✅ Track Sales Performance: See which products are selling and which aren't
✅ Identify Profitable Items: Know which products give you the best margins
✅ Prevent Stock Issues: Avoid overstocking slow-moving items
✅ Make Data-Driven Decisions: Use real numbers instead of guesswork
✅ Save Time: Automated analysis instead of manual calculations
✅ Smart Period Detection: Automatically recognizes date ranges in filenames
✅ Comprehensive Reports: Multi-period selection for detailed analysis

---

# 2. Getting Started

### Accessing the Application
1. Open your web browser (Chrome, Firefox, or Edge recommended)
2. Navigate to your application URL
3. The dashboard will load automatically

### Understanding the Interface
The application has 7 main tabs at the top:
1. **Daily Upload Dashboard** - Overview of your business performance and daily data upload
2. **Daily Sales Report** - Generate daily financial reports
3. **Detailed Analytics** - Advanced analysis and insights
4. **Forecasting** - Predict future sales
5. **Bulk Data Upload** - Upload monthly/yearly sales files
6. **Upload History** - Track what data has been uploaded
7. **Database View** - View and search all records with admin tools

### Key Metrics Summary
At the top of every page, you'll see important numbers:
* **Total Revenue**: Total sales amount
* **Total Profit**: Your earnings after costs
* **Current Stock Value**: Latest stock value from financial reports (with refresh button)
* **C Category Stock**: Low-value inventory tracking
* **Profit Margin**: Profit percentage (higher is better)

---

# 3. Daily Upload Dashboard Tab

The Dashboard is your daily command center with responsive design and real-time insights.

### What You'll See

#### A. Upload Today's Sales Button
**Purpose**: Quick access to upload your daily sales report
**When to Use**: At the end of each business day
**How to Use**:
1. Click the blue "Upload Today's Data" button
2. Select today's date
3. Choose your Excel file
4. Click "Upload"

#### B. Daily Sales Trend Chart
* Line chart showing daily sales for current quarter
* 3 months displayed with different colors
* Each day's sales plotted as data points
* Monthly totals shown below chart
* Hover over points to see exact amounts
* Helps identify daily patterns and trends

#### C. Group Performance Chart
**What it Shows**:
* Blue bars = Total revenue from each product group
* Green bars = Total profit from each product group

**Why it Matters**:
* Helps identify which product categories are most profitable
* Shows if you should focus more on certain groups

#### D. Top Selling Items
* **Dynamic selector** to switch between:
  * By Quantity: Units sold (Blue)
  * By Revenue: Money earned (Green)
  * By Profit: Actual profit (Orange)
* Color-coded cards for easy identification
* Shows additional metrics below each item
* Rank numbers highlighted

**How to Use**:
1. Click the dropdown that says "View by:"
2. Select Quantity Sold / Revenue / Profit
3. The list automatically updates

**Pro Tip**: Items may rank differently by each metric. An item can sell many units (high quantity) but give low profit!

---

# 4. Bulk Data Upload Tab

This is where you upload your monthly or yearly sales reports.

### Smart Period Detection (NEW in v3.2!)
The system now automatically recognizes period information from your filename:

**Supported Filename Formats**:
* **Range periods**: "Jan to Sep 2025.xlsx" → Stores as "Jan-Sep 2025"
* **Single month**: "Nov 2025.xlsx" → Stores as "Nov 2025"
* **Monthly with dates**: "01 to 30 Oct 25.xlsx" → Stores as "Oct 2025"
* **Yearly**: "YR 2024.xlsx" → Stores as "2024"

**How It Works**:
1. Upload a file named "Jan to Sep 2025.xlsx"
2. System detects it contains 9 months of data
3. Period automatically stored as "2025-01-09" (internal format)
4. Displays as "Jan-Sep 2025" everywhere in the app
5. Shows consistently in Analytics dropdown and Report generation

### File Requirements
**Accepted Formats**: `.xlsx` or `.xls` files

**Required Columns**:
* S.No or GP_Index_No
* Item_Name
* Qty (Quantity Sold)
* R_Rate (Retail Rate)
* W_Rate (Wholesale Rate)
* R_Amt (Retail Amount)
* W_Amt (Wholesale Amount)
* Closing_Stock

### How to Upload Historical Data
**Step 1**: Click "Bulk Data Upload" tab
**Step 2**: Click "Choose Excel File" or drag your file
**Step 3**: Wait for file validation
* ✅ Green checkmark = File accepted
* ❌ Red error = File has issues

**Step 4**: Review the upload summary
* Number of records found
* **Period automatically detected** from filename
* Sample items shown

**Step 5**: Click "Confirm Upload"
**Step 6**: Wait for processing
**Step 7**: Success! Period now appears formatted in all dropdowns

### Period Naming Best Practices
For best automatic detection, name your files:
* Full range: "Jan to Sep 2025.xlsx" or "01 Jan to Sep 30 2025.xlsx"
* Single month: "Nov 2025.xlsx" or "November 2025.xlsx"
* With dates: "01 to 30 Oct 25.xlsx"
* Full year: "YR 2024.xlsx" or "2024.xlsx"

---

# 5. Upload History Tab

Track all your data uploads and manage them.

### What You'll See
Each upload shows:
* Upload Date: When you uploaded the file
* File Name: Original Excel file name
* **Period Covered**: Formatted period (e.g., "Jan-Sep 2025" or "Nov 2025")
* Records Count: Number of items uploaded
* Status: Success ✅ or Failed ❌
* Actions: UNDO button

### How to Use the UNDO Feature
**When to Use**: If you uploaded wrong data or need to replace an upload

**How to UNDO**:
1. Find the upload you want to remove
2. Click the red "UNDO" button
3. Confirm you want to delete
4. All records from that upload will be removed

⚠️ **Warning**: UNDO cannot be reversed! Make sure before clicking.

---

# 6. Database View Tab

See all your sales records in one place with administrative tools.

### Period Migration Tool (NEW in v3.2!)

**⚡ One-Time Migration Section**
Located at the top in a yellow box:

**What It Does**:
* Fixes period format for data uploaded before the latest update
* Updates old "Jan 2025" records to proper "Jan-Sep 2025" range format
* One-click operation from your mobile or desktop

**When to Use**:
* After deploying the latest update
* If you uploaded "Jan-Sep 2025" data before and it shows as just "Jan 2025"
* Only need to run once

**How to Use**:
1. Click on "Database View" tab
2. Look for yellow box "⚡ One-Time Migration"
3. Click orange "Run Migration" button
4. Confirm when prompted
5. Wait for success message
6. View refreshes automatically

**What Happens**:
* Scans database for incorrectly formatted periods
* Updates to proper range format
* Shows count of updated records
* **Example**: Updates 2,530 records from "2025-01" → "2025-01-09" (displays as "Jan-Sep 2025")

### Database Search and View
**Search Box**: Type item name or code to find specific products

**How to Sort**: Click any column header to sort

**Pagination**: Choose rows per page and navigate

**Exporting Data**: Click "Export" button to download

---

# 7. Detailed Analytics Tab

This is your most powerful tool for business insights! The Analytics tab has 4 sub-sections with period filtering.

### Period Filter (NEW - Consistent Formatting!)
**Located at top of Analytics tab**

**What You'll See**:
* Formatted period names matching report generation
* **Current Period (Dec 2025)** - Auto-detected current month
* **Nov 2025** - Individual months
* **Jan-Sep 2025** - Multi-month ranges
* **2024, 2023, 2022** - Full years

**How It Works**:
* Same periods as report generation modal
* Select period to filter all analytics
* Updates all 4 sub-sections
* Consistent formatting everywhere

### A. Performance Analysis

**Purpose**: Understand which products are truly your best performers

**Metric Selector Feature**:
* Quantity Sold - Units sold (Blue charts)
* Revenue Generated - Money earned (Green charts)
* Profit Earned - Actual profit (Orange charts)

**The Three Lists**:
1. Top Performers by Selected Metric
2. Their Second Metric
3. Their Third Metric

**Why This Matters**:
* An item can be #1 in sales but #10 in profit!
* Focus on profit for better business decisions

### B. ABC Analysis

**Purpose**: Classify your inventory using the 80/20 rule

**Categories**:
* **Category A** - Fast Moving (Green): Top 20% items = 80% revenue
* **Category B** - Medium Moving (Blue): Next 30% items = 15% revenue
* **Category C** - Slow Moving (Red): Bottom 50% items = 5% revenue

**How to Use for Inventory**:
* Category A: Never run out, prime placement
* Category B: Adequate stock, standard placement
* Category C: Minimize stock, consider removing

### C. Capital Blocking Analysis

**Purpose**: Identify items tying up your money

**Risk Levels**:
* **CRITICAL (Red)**: > ₹50,000 blocked, > 1 year to sell
* **HIGH (Orange)**: > ₹10,000 blocked, > 6 months to sell
* **MEDIUM (Yellow)**: > ₹5,000 blocked, > 3 months to sell
* **LOW (Gray)**: Lesser amounts or faster movement

**Smart Sorting**:
* Items automatically sorted by risk level first
* Critical items appear at top (most urgent)
* Focus on items that will NEVER sell

### D. Inventory Health

**Three Health Indicators**:
1. **Dead Inventory (Red Alert)**: Zero sales but still have stock
2. **Slow Moving (Orange Alert)**: < 5 units per month
3. **High Cost, Poor Performance (Yellow Alert)**: Expensive items not selling well

**Action Steps**: Review weekly and implement clearance strategies

---

# 8. Forecasting Tab

**Purpose**: Predict future sales to plan better

### How to Generate Forecast
1. Select forecast month
2. Choose forecast method (Trend/Statistical/AI)
3. Click "Generate Forecast"
4. Review predicted quantities and recommended stock levels

**Use For**:
* Order inventory based on predictions
* Plan promotions for high-demand months
* Adjust staffing levels

---

# 9. Daily Sales Report Tab

**Purpose**: Track and manage daily financial position

### Generating Daily Financial Reports

**Step 1**: Access Report Generation
* Click "Daily Sales Report" tab
* Click green "Generate Daily Report" button

**Step 2**: Fill Report Details
* **Report Date**: Select the date
* **Sales Information**:
  * Liquor Sales: Enter manually (required)
  * Grocery Sales: Auto-calculated from daily upload
* **Previous Day Balances**: Auto-populated from yesterday
* **Current Stock Value**: Leave blank for auto-calculation

**Step 3**: Generate Report
* Click "Generate & Download PDF"
* Report downloads automatically
* Data saved to database

### Managing Previous Reports

**Edit a Report**:
1. Find report in the table
2. Click blue ✏️ Edit button
3. Modify values
4. Click "Update Report"

**Delete a Report**:
1. Find report in the table
2. Click red 🗑️ Delete button
3. Confirm deletion

---

# 10. Report Generation

### Multi-Select Period Feature (NEW in v3.2!)

**Location**: Click "Excel Report" or "PDF Report" buttons at top-right

**How It Works**:
1. Dialog opens with list of all available periods
2. **All periods pre-selected** by default
3. Select/deselect specific periods using checkboxes
4. "Select All / Deselect All" toggle button
5. Shows count: "X periods selected"
6. Click "Generate Report"

**Period Format in Dialog**:
* **Current Period (Dec 2025)** - This month's data
* **Nov 2025** - Individual monthly data
* **Jan-Sep 2025** - Multi-month range data
* **2024, 2023, 2022** - Full year data

**Selection Options**:
* Select multiple periods: Generate combined report
* Select single period: Specific period analysis
* Select all: Complete historical analysis

**Report Titles**:
* Single period: "Report - Nov 2025"
* Two periods: "Report - Nov 2025 & 2024"
* Multiple: "Report - Nov 2025, Oct 2025, 2024"
* Many: "Report - Nov 2025 to 2022 (5 periods)"

**Validation**:
* Cannot generate report with no periods selected
* Error message: "Please select at least one period for the report"

**Benefits**:
* Compare performance across specific months
* Generate reports for financial quarters
* Analyze year-over-year trends
* Custom time period analysis

---

# 11. Understanding Your Reports

### Excel Report (7 Sheets)

**Sheet 1: Executive Summary**
* Total Revenue, Profit, Margin
* **Period covered** shown in title
* All values in Indian Number System (₹23,92,58,751.93)

**Sheet 2: ABC Analysis**
* Category A (High Value): 7-10% items = 80% revenue
* Category B (Medium Value): 10-15% items = 15% revenue
* Category C (Low Value): 75-83% items = 5% revenue
* Recommendations for each category

**Sheet 3: Capital Blocking**
* Top 50 items blocking capital
* Risk levels (Critical/High/Medium)
* Days to sell calculation

**Sheet 4: Group Performance**
* Revenue and profit by product group
* **Group data now showing correctly** (Group VI, Group III, etc.)
* Profit margins per group

**Sheet 5: Top Performers**
* Top 20 best-selling items
* Revenue, profit, and margin data
* **Group column populated** with actual group names

**Sheet 6: Items to Liquidate**
* 20 slowest-moving items
* Capital blocked per item
* Action required (Urgent/Plan Clearance)

**Sheet 7: Smart Recommendations**
* Immediate actions for capital optimization
* 3-month procurement strategy
* Product group optimization
* Profit maximization plan

### PDF Report
Same structure as Excel with professional formatting:
* **Period shown in report title**
* All amounts shown as "Rs" (Rs 23,92,58,751.93)
* Indian Number System formatting
* Color-coded sections
* Ready to print or present

---

# 12. Best Practices

### Daily Tasks
**For Data Entry Clerk**:
1. Upload today's sales data (end of day)
2. Enter financial health numbers
3. Check for upload errors
4. **Verify period shows correctly**

**For Store Manager**:
1. Review dashboard in morning
2. Check inventory alerts
3. **Use multi-period reports** for trend analysis

### Weekly Tasks
**For Inventory Manager**:
1. Review top sellers - ensure adequate stock
2. Check slow-moving items - adjust orders
3. **Generate weekly reports** with last 7 days
4. Export analytics report

### Monthly Tasks
**For Management**:
1. Upload monthly historical data with proper filename (e.g., "Nov 2025.xlsx")
2. Complete ABC analysis review
3. Capital blocking action plan
4. **Generate multi-period report** (current month + last 3 months)
5. Forecasting for next month

### After New Deployment
1. **Run migration** from Database View tab (one-time)
2. Verify periods show correctly in Analytics dropdown
3. Test report generation with multiple periods
4. Confirm group data displays properly

---

# 13. Troubleshooting

### Common Issues and Solutions

#### Issue: Periods showing as "Jan 2025" instead of "Jan-Sep 2025"
**Solution**:
1. Go to Database View tab
2. Click "Run Migration" button in yellow box
3. Wait for confirmation
4. Refresh browser

#### Issue: Different periods in Analytics vs Reports
**Solution**: 
* Update to latest version
* Run migration in Database View
* Periods will now match everywhere

#### Issue: Upload shows wrong period
**Solution**:
* Check filename matches supported formats
* Use format: "Jan to Sep 2025.xlsx" or "Nov 2025.xlsx"
* Avoid complex date formats in filename

#### Issue: Group showing as "NA" in reports
**Solution**:
* This is fixed in v3.2
* Group data now shows correctly (Group VI, Group III, etc.)
* Regenerate reports after update

#### Issue: Cannot generate report - no periods selected
**Solution**:
* At least one period must be selected
* Check if any checkboxes are checked
* Use "Select All" button to select all periods

---

## Glossary of Terms

* **ABC Analysis**: Inventory classification method (80/20 rule)
* **Capital Blocking**: Money tied up in unsold inventory
* **Dead Inventory**: Stock with zero sales
* **Multi-Select Period**: Select multiple time periods for combined report
* **Period Range**: Data spanning multiple months (e.g., Jan-Sep 2025)
* **Group**: Product category (Group I, II, III, IV, VI)
* **Smart Period Detection**: Automatic recognition of date ranges from filenames

---

## Version History

**Version 3.2 (Current - December 2025)**
* ✅ Smart period detection from filenames
* ✅ Multi-select period report generation
* ✅ Period consistency across all features
* ✅ Migration tool in Database View
* ✅ Fixed group data display (Group VI, etc.)
* ✅ Updated tab names for clarity
* ✅ Current month auto-detection

**Version 3.1**
* Financial report editing and deletion
* Indian Number System formatting
* Enhanced recommendations

**Version 3.0**
* Analytics tab with 4 sub-sections
* ABC analysis and capital blocking
* Inventory health tracking

**Version 2.0**
* Advanced filtering and sorting
* Dashboard enhancements

**Version 1.0**
* Initial release

---

## End of User Handbook

**Version 3.2** | Updated: December 2025 | URC 101 Grocery Sales Analytics

For additional support or questions, please contact your system administrator.
