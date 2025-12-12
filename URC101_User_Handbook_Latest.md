# URC 101 Grocery Sales Analytics - Complete User Handbook
## Version 3.3 - December 2025 - Latest Release
**Comprehensive Guide for All Users**

---

## Table of Contents
1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Tab 1: Daily Upload Dashboard](#3-tab-1-daily-upload-dashboard)
4. [Tab 2: Daily Sales Report](#4-tab-2-daily-sales-report)
5. [Tab 3: Detailed Analytics](#5-tab-3-detailed-analytics)
6. [Tab 4: Forecast](#6-tab-4-forecast)
7. [Tab 5: Bulk Data Upload](#7-tab-5-bulk-data-upload)
8. [Tab 6: Upload History](#8-tab-6-upload-history)
9. [Tab 7: Database View](#9-tab-7-database-view)
10. [Report Generation System](#10-report-generation-system)
11. [Understanding Reports](#11-understanding-reports)
12. [Best Practices](#12-best-practices)
13. [Troubleshooting](#13-troubleshooting)

---

# 1. Introduction

## What is URC 101 Grocery Sales Analytics?

URC 101 is a comprehensive, data-driven platform designed specifically for grocery store management. It transforms your raw sales data into actionable insights, helping you make informed decisions about inventory, pricing, and profitability.

## Who Should Use This App?

**Store Managers**: Get real-time insights into business performance and trends
**Inventory Managers**: Optimize stock levels and identify problem items
**Data Entry Clerks**: Upload and manage daily/monthly sales data
**Business Owners**: Make strategic decisions based on comprehensive analytics
**Accountants**: Track financial health and generate reports

## Key Features at a Glance

✅ **Smart Period Detection**: Automatically recognizes date ranges from filenames ("Jan to Sep 2025")
✅ **Multi-Period Reports**: Select and combine multiple time periods for analysis
✅ **Real-Time Dashboard**: Daily sales trends, group performance, top sellers
✅ **Advanced Analytics**: ABC analysis, capital blocking, inventory health
✅ **Financial Tracking**: Daily reports with auto-calculations
✅ **Forecasting**: AI-powered sales predictions
✅ **Export Everything**: Download data in Excel, CSV, or PDF formats
✅ **Period Consistency**: Same formatted periods across all features
✅ **Latest Rates**: Aggregated views show most recent prices
✅ **Chunked Exports**: Handle large datasets (20K+ records) efficiently

---

# 2. Getting Started

## Accessing the Application

1. Open your web browser (Chrome, Firefox, Safari, or Edge)
2. Navigate to your application URL
3. The dashboard loads automatically - no login required

## Understanding the Interface

### Top Navigation Bar
Contains:
* **Total Revenue** - All-time sales total
* **Total Profit** - Total earnings after costs
* **Current Stock Value** - Latest stock valuation (with 🔄 refresh button)
* **Profit Margin** - Overall profitability percentage
* **Excel Report** & **PDF Report** buttons - Multi-period report generation

### Tab Navigation (7 Tabs)
Arranged left to right:

**Color Key**:
* 🔵 Blue - Daily Upload Dashboard
* 🟢 Green (Emerald) - Daily Sales Report  
* 🟣 Purple - Detailed Analytics
* 🟠 Orange - Forecast
* 🟢 Green - Bulk Data Upload
* 🔵 Indigo - Upload History
* 🔵 Cyan - Database View

### Period Display Format
Throughout the app, you'll see periods formatted as:
* **"Current Period (Dec 2025)"** - This month's ongoing data
* **"Nov 2025"** - Complete month of November
* **"Jan-Sep 2025"** - Multi-month range (9 months)
* **"2024"** - Complete year

**Note**: These formats are consistent everywhere - Dashboard, Analytics, Reports, and Database View!

---

# 3. Tab 1: Daily Upload Dashboard

**Purpose**: Your daily command center for monitoring business performance

## What You'll See

### A. Key Metrics Cards (Top Section)
Four responsive cards that adapt to screen size:
* **Total Records** - Number of sales transactions
* **Total Items Sold** - Unit count
* **Average Revenue** - Per-period revenue
* **Data Coverage** - Date range of your data

### B. Upload Today's Sales Button
* Large blue button for quick daily upload
* Opens date selector for today's date
* Same as daily upload in Daily Sales Report tab
* Use this at end of each business day

### C. Daily Sales Trend Chart (NEW Feature!)
**What it shows**:
* Line chart displaying 3 months of daily sales
* Current quarter (e.g., Oct, Nov, Dec)
* Each day plotted as a data point
* Monthly totals shown below chart
* Hover over points to see exact amounts

**Why it matters**:
* Identify daily patterns (weekday vs weekend)
* Spot unusual spikes or drops
* Track month-over-month trends
* Validate data entry accuracy

### D. Group Performance Charts

**Dual Bar Chart**:
* **Blue bars** - Total Revenue by product group
* **Green bars** - Total Profit by product group
* Groups sorted by revenue (highest first)

**Pie Chart**:
* Shows revenue distribution across groups
* Percentage labels on each slice
* Helps identify which categories dominate sales

**Why useful**: Instantly see which product categories drive your business

### E. Top Selling Items (Dynamic)

**Metric Switcher** (Dropdown selector):
Choose from:
1. **Quantity Sold** (Blue cards) - Most popular items by units
2. **Revenue Generated** (Green cards) - Highest sales value
3. **Profit Earned** (Orange cards) - **Most important for profitability!**

**Each card shows**:
* Rank number (1, 2, 3...)
* Item name
* Product group
* Primary metric (large number)
* Secondary metrics below

**Pro Tip**: An item can be #1 in quantity but #10 in profit! Always check the Profit view to optimize for earnings.

### F. Inventory Alerts

Three alert categories with counts:
* 🔴 **Dead Inventory** - Items with zero sales but in stock
* 🟠 **Slow Moving** - Items selling < 5 units per month
* 🟡 **High Cost Poor Performance** - Expensive items not selling

Click "View Details" to see the full list

### G. Group Performance Summary Table
Detailed breakdown showing:
* Group name
* Total revenue
* Total profit
* Profit margin %
* Item count in group

---

# 4. Tab 2: Daily Sales Report

**Purpose**: Generate and manage daily financial reports with auto-calculations

## Generating Daily Financial Reports

### Step 1: Access the Report Form
Click "Daily Sales Report" tab → Click green "Generate Daily Report" button

### Step 2: Fill in Required Information

**Report Date**: Select the date for this report

**Sales Data**:
* **Liquor Sales** - Manual entry (required)
* **Grocery Sales** - **Auto-calculated** from your uploaded daily data

**Previous Day's Data** (Auto-filled from yesterday's report):
* Previous Bank Balance
* Previous OLX Balance  
* Previous Stock Value

**Today's Closing** (Manual entry):
* Today's Bank Balance
* Today's OLX Balance
* **Current Stock Value** - Leave blank for auto-calculation OR enter manually

### Step 3: Auto-Calculations
When you leave Current Stock Value blank, the system:
1. Finds today's sales data from database
2. Calculates: `Opening Stock - Items Sold + Any Additions`
3. Multiplies quantities by latest rates
4. Provides accurate stock valuation

### Step 4: Generate Report
* Click "Generate & Download PDF" button
* Report downloads immediately
* Data saved to database
* **Dashboard automatically updates** with new stock value

## Managing Previous Reports

### View All Reports
Table showing all generated reports with:
* Report date
* Liquor sales
* Grocery sales
* Bank balance
* Stock value
* Actions (Edit/Delete)

### Edit a Report
1. Find the report in table
2. Click blue ✏️ **Edit** button
3. Modify any values
4. Click "Update Report"
5. Dashboard refreshes with new values

### Delete a Report
1. Find the report in table
2. Click red 🗑️ **Delete** button  
3. Confirm deletion
4. Report removed from database

**Important**: Deleting a report also removes it from dashboard history

---

# 5. Tab 3: Detailed Analytics

**Purpose**: Advanced business intelligence with 4 powerful sub-sections

## Filter Controls (Top of Page)

### Group Filter
Select specific product groups or "All Groups"

### Period Filter (Consistent Formatting!)
**What you'll see**:
* Current Period (Dec 2025) - This month
* Nov 2025 - Individual months
* Oct 2025
* Jan-Sep 2025 - Multi-month ranges
* 2024, 2023, 2022 - Full years

**How it works**:
* Same periods as report generation
* Select to filter ALL 4 sub-sections simultaneously
* Updates all charts and tables instantly

## Sub-Section A: Performance Analysis

### Metric Selector (Enhanced Feature)
**Three viewing modes**:
1. **Quantity Sold** (Blue) - Physical units moved
2. **Revenue Generated** (Green) - Money brought in
3. **Profit Earned** (Orange) - **Most important!**

### Three Interactive Charts
When you select a metric:
* **Primary Chart** - Top items by selected metric
* **Relationship Chart 1** - How primary relates to second metric
* **Relationship Chart 2** - How primary relates to third metric

**Example**: Select "Revenue Generated"
* Chart 1: Top 10 by Revenue
* Chart 2: Revenue vs Quantity (bar comparison)
* Chart 3: Revenue vs Profit (bar comparison)

### The Tables
Below charts, see three ranked lists:
* **By Primary Metric** - Sorted by your selection
* **By Second Metric** - Same items, different ranking
* **By Third Metric** - Same items, yet another ranking

**Why This Matters**:
* Item ranked #1 in sales might be #15 in profit!
* Focus on profit leaders, not just popular items
* Make inventory decisions based on earnings, not volume

### Export Button
Download current view as Excel file with period in filename

---

## Sub-Section B: ABC Analysis

**Purpose**: Classify your entire inventory using the Pareto Principle (80/20 rule)

### The Three Categories

**Category A - Fast Moving (Green)**
* **Who they are**: Top 20% of items by sales volume
* **Revenue contribution**: Generate 80% of your revenue
* **Stock strategy**: NEVER run out of these!
* **Placement**: Prime shelf locations
* **Ordering**: Generous stock levels, frequent reorders

**Category B - Medium Moving (Blue)**  
* **Who they are**: Next 30% of items
* **Revenue contribution**: Generate 15% of revenue
* **Stock strategy**: Maintain adequate levels
* **Placement**: Standard shelf locations
* **Ordering**: Moderate stock, regular reorders

**Category C - Slow Moving (Red)**
* **Who they are**: Bottom 50% of items
* **Revenue contribution**: Only 5% of revenue
* **Stock strategy**: Minimize inventory
* **Placement**: Back shelves or low visibility
* **Ordering**: Order to cover demand only, consider discontinuing

### How to Read the Display

**Summary Cards**:
* Category A: X items, ₹XX,XXX total revenue (80%)
* Category B: Y items, ₹YY,YYY total revenue (15%)
* Category C: Z items, ₹ZZ,ZZZ total revenue (5%)

**Detailed Tables**:
Each category shows:
* Item code and name
* Product group
* Total quantity sold
* Total revenue
* Revenue percentage contribution

### Practical Example
If you have 1,000 items:
* Category A: ~200 items earn ₹80 lakhs (focus here!)
* Category B: ~300 items earn ₹15 lakhs (maintain)
* Category C: ~500 items earn ₹5 lakhs (reduce/remove)

### Export ABC
Download complete ABC classification as Excel

---

## Sub-Section C: Capital Blocking Analysis

**Purpose**: Identify items tying up your money in unsold inventory

### Understanding Capital Blocking
Money "blocked" = (Closing Stock Units × Wholesale Rate per Unit)

This is cash you've spent but haven't recovered through sales.

### Risk Levels (Smart Sorting)

**CRITICAL (Red)**
* **Capital Blocked**: > ₹50,000
* **Days to Sell**: > 365 days (over a year!)
* **Action Required**: URGENT - Clear immediately
* **Strategies**: Deep discounts, return to supplier, bulk sale

**HIGH (Orange)**
* **Capital Blocked**: > ₹10,000
* **Days to Sell**: > 180 days (6+ months)
* **Action Required**: Clearance sale within 30 days
* **Strategies**: Bundle deals, promotions, alternate channels

**MEDIUM (Yellow)**
* **Capital Blocked**: > ₹5,000  
* **Days to Sell**: > 90 days (3+ months)
* **Action Required**: Monitor closely, reduce orders
* **Strategies**: Small discounts, featured placement

**LOW (Gray)**
* **Capital Blocked**: < ₹5,000
* **Days to Sell**: < 90 days
* **Action Required**: Normal monitoring
* **Strategies**: Continue current approach

### How Items Are Sorted
**Automatic smart sorting**:
1. First by risk level (Critical → High → Medium → Low)
2. Within each level, by capital amount (highest first)

This ensures the most urgent items appear at the top!

### Table Columns
* Item Code & Name
* Product Group
* Closing Stock (units)
* Days to Sell (based on average daily sales)
* Capital Blocked (₹)
* Risk Level
* Recommendation

### Sample Capital Blocking Entry
```
PREMIUM OIL 5L | Group II | 250 units | 450 days | ₹65,000 | CRITICAL
→ Recommendation: Immediate clearance - Return or discount 40%
```

### Export Capital Blocking
Download full analysis with all risk levels

---

## Sub-Section D: Inventory Health

**Purpose**: Three critical health checks for your inventory

### 1. Dead Inventory (Red Alert) 🔴

**Definition**: Items with closing stock > 0 BUT zero sales in period

**Why dangerous**:
* Money completely wasted
* Storage space occupied
* Will never recover investment
* Potential expiry/damage

**What you see**:
* Item name and code
* Product group
* Units in stock
* **Sale status**: "0 sales"
* Capital trapped

**Action Steps**:
1. Immediate clearance at ANY price
2. Liquidate within 7 days
3. Recover whatever you can
4. Free up cash and space
5. NEVER reorder these items

**Example**:
```
EXOTIC SPICE MIX | 150 units | 0 sales | ₹22,500 blocked
→ Action: Sell at 50% off or donate for tax benefits
```

### 2. Slow Moving (Orange Alert) 🟠

**Definition**: Items selling < 5 units per month

**Why concerning**:
* Tying up capital unnecessarily
* Risk of becoming dead stock
* Better alternatives might exist
* Storage cost exceeds profit

**What you see**:
* Item details
* **Monthly sales rate**: "< 5 units/month"
* Stock level
* Projected days to clear current stock

**Action Steps**:
1. Stop reordering immediately
2. Let existing stock sell naturally
3. Create small promotions to accelerate
4. Replace with better-selling alternatives
5. Monitor for 2 months then decide fate

**Example**:
```
GOURMET SAUCE 500ML | 3 units/month | 60 units stock
→ Projected: 20 months to clear
→ Action: Stop orders, small discount, replace if no improvement
```

### 3. High Cost, Poor Performance (Yellow Alert) 🟡

**Definition**: Expensive items (high wholesale cost) that aren't selling well

**Why concerning**:
* Large investment per unit
* Slow turnover = high risk
* Premium items need premium sales
* Alternative cheaper options may work better

**What you see**:
* Item details
* **Wholesale rate**: High value (e.g., > ₹500)
* **Performance**: Low sales relative to cost
* Margin analysis

**Action Steps**:
1. Evaluate if premium pricing is justified
2. Check if cheaper alternatives sell better
3. Consider replacing with mid-range options
4. If keeping, improve visibility and marketing
5. Set minimum sales threshold - remove if not met

**Example**:
```
IMPORTED CHEESE 1KG | W_Rate: ₹850 | 8 units/month
→ Similar local cheese: ₹350, 45 units/month
→ Action: Test local alternative, phase out import
```

### How to Use Inventory Health

**Weekly Review** (15 minutes):
1. Check dead inventory count - act on any additions
2. Review slow moving items - adjust orders
3. Evaluate high-cost items - track performance

**Monthly Deep Dive** (1 hour):
1. Calculate total capital in problem inventory
2. Set clearance targets
3. Implement action plans
4. Track week-by-week improvements

**Quarterly Assessment**:
1. Measure success of clearance efforts
2. Identify recurring problem categories
3. Adjust buying patterns permanently

### Export Inventory Health
Download complete health analysis with all three categories

---

# 6. Tab 4: Forecast

**Purpose**: Predict future sales to plan inventory and promotions

## How Forecasting Works

The system analyzes your historical sales patterns to predict future demand using three methods:

### Forecasting Methods Available

**1. Trend-Based Forecasting**
* Analyzes long-term growth or decline patterns
* Best for: Stable, mature product lines
* Time needed: Minimum 6 months of data

**2. Statistical Forecasting**
* Uses moving averages and seasonal patterns
* Best for: Items with predictable seasonality
* Time needed: Minimum 12 months of data

**3. AI-Powered Forecasting** (Advanced)
* Machine learning algorithms
* Considers multiple variables simultaneously
* Best for: Complex patterns, new items
* Time needed: Minimum 3 months of data

## Generating a Forecast

### Step 1: Select Forecast Month
Choose the future month you want to predict (e.g., "January 2026")

### Step 2: Choose Forecasting Method
Select from Trend, Statistical, or AI based on your data

### Step 3: Select Product Group (Optional)
* Choose "All Groups" for complete forecast
* Or select specific group for detailed analysis

### Step 4: Click "Generate Forecast"
System processes data and displays predictions

## Reading Your Forecast

### Forecast Table Shows:
* **Item Code & Name**
* **Product Group**
* **Historical Average** - Past monthly sales
* **Predicted Quantity** - Forecasted sales
* **Confidence Level** - Accuracy indicator (Low/Medium/High)
* **Recommended Order Quantity** - Suggested purchase amount
* **Current Stock** - What you have now
* **Stock Status** - Adequate, Low, or Overstocked

### Confidence Levels Explained

**High Confidence (Green)** - 85%+ accuracy
* Strong historical pattern
* Reliable prediction
* Order with confidence

**Medium Confidence (Yellow)** - 70-84% accuracy
* Moderate pattern consistency  
* Good prediction with some variation
* Order but monitor closely

**Low Confidence (Red)** - Below 70% accuracy
* Irregular sales pattern
* Less reliable prediction
* Use as rough guide only, order conservatively

## Using Forecasts Effectively

**For Inventory Planning**:
1. Check "Recommended Order Quantity"
2. Compare with "Current Stock"
3. Calculate: Order = Recommended - Current
4. Adjust based on supplier minimums

**For Promotion Planning**:
* High predicted demand → Plan adequate stock
* Low predicted demand → Consider promotions
* Compare groups → Allocate marketing budget

**For Staffing**:
* High volume months → Schedule extra staff
* Low volume months → Reduce hours

**Best Practices**:
* Generate monthly forecasts
* Compare predictions vs actual sales
* Adjust ordering patterns over time
* Don't rely 100% on forecasts - use judgment too

## Exporting Forecasts

Click "Export Forecast" to download Excel file with:
* Complete forecast data
* Charts comparing historical vs predicted
* Recommended actions per item

---

# 7. Tab 5: Bulk Data Upload

**Purpose**: Upload historical sales data (monthly, yearly, or multi-month periods)

## Smart Period Detection (Key Feature!)

The system automatically recognizes period information from your filename!

### Supported Filename Formats

**Multi-Month Ranges**:
* `"Jan to Sep 2025.xlsx"` → Stored as "Jan-Sep 2025" (9 months)
* `"01 Jan to Sep 30 2025.xlsx"` → Same result
* `"Apr to Dec 2024.xlsx"` → Stored as "Apr-Dec 2024"

**Single Months**:
* `"Nov 2025.xlsx"` → Stored as "Nov 2025"
* `"November 2025.xlsx"` → Same result
* `"01 to 30 Oct 25.xlsx"` → Stored as "Oct 2025"

**Full Years**:
* `"YR 2024.xlsx"` → Stored as "2024"
* `"2024.xlsx"` → Same result
* `"Year 2023 Complete.xlsx"` → Stored as "2023"

**Current Month**:
* Data for December 2025 → Auto-detected as "Current Period (Dec 2025)"

### How Smart Detection Works

1. You name file: `"Jan to Sep 2025.xlsx"`
2. System extracts: Year=2025, Start=January, End=September
3. Internally stores as: `"2025-01-09"` (database format)
4. Displays everywhere as: `"Jan-Sep 2025"` (user-friendly format)
5. Shows consistently in:
   - Detailed Analytics dropdown
   - Report generation modal
   - Database View filter
   - Dashboard period selector

**Pro Tip**: Use clear filenames! The smarter your naming, the more accurate the detection.

## File Requirements

### Accepted Formats
* `.xlsx` (Excel 2007+)
* `.xls` (Excel 97-2003)

### Required Columns

**Must Have** (System won't work without these):
* `Item_Name` or `item_name` - Product name
* `Qty` or `qty` or `net_qty` - Units sold
* `R_Amt` or `r_amt` - Retail amount (sales value)
* `W_Amt` or `w_amt` - Wholesale amount (cost)

**Highly Recommended**:
* `S.No` or `GP_Index_No` or `gp_index_no` - Unique item code
* `Product_Group` or `product_group` - Category
* `R_Rate` - Retail rate per unit
* `W_Rate` - Wholesale rate per unit
* `Closing_Stock` - Ending inventory
* `Opening_Balance` or `O_B` - Starting inventory

**Optional but Useful**:
* `Net_Tax` - Tax amount
* `Data_Date` - Specific transaction date

### Data Format Guidelines

**Numbers**:
* Use regular numbers: `123.45` ✅
* Avoid currency symbols: `₹123.45` ❌
* Avoid commas in numbers: `1,234` ❌ → Use `1234` ✅

**Text**:
* Item names can have spaces and special characters
* Product groups should be consistent (e.g., always "Group I", not "GroupI" or "Group 1")

**Empty Cells**:
* Empty qty/amounts treated as zero
* Empty text fields treated as blank
* Don't use "-" or "N/A" - leave truly empty

## Step-by-Step Upload Process

### Step 1: Click "Bulk Data Upload" Tab
Blue/Green upload interface appears

### Step 2: Choose Your File
* Click "Choose Excel File" button OR
* Drag and drop your .xlsx file onto the upload area

### Step 3: File Validation (Automatic)
System checks:
* ✅ File format valid
* ✅ Required columns present
* ✅ Data can be read
* ✅ Period detected from filename

**If validation fails**, you'll see:
* ❌ Red error message explaining issue
* List of missing columns (if any)
* File size error (if too large)

### Step 4: Review Upload Summary
System shows:
* **Number of records found**: e.g., "1,245 valid records"
* **Period detected**: e.g., "Jan-Sep 2025" 
* **Sample items**: First 5-10 items preview
* **Data type**: Historical/Monthly/Yearly
* **Date range**: If dates detected

**Verify this information is correct!**

### Step 5: Handle Period Conflicts
If data for this period already exists:
* ⚠️ Warning message appears: "Data for Jan-Sep 2025 already exists"
* **Options**:
  1. Cancel upload, check existing data
  2. Go to Upload History and UNDO previous upload
  3. Re-upload after removing old data

**Why prevent duplicates?**
* Avoids double-counting sales
* Maintains data accuracy
* Prevents inflated numbers in reports

### Step 6: Confirm Upload
* Click "Confirm Upload" button
* Progress bar appears
* System processes records (takes 10-60 seconds for large files)

### Step 7: Upload Success
* ✅ Green success message
* Summary shows:
  * Records uploaded
  * Period stored
  * Processing time
* **Period now appears in all dropdowns** formatted correctly
* Dashboard and Analytics automatically include new data

## Common Upload Errors and Solutions

### Error: "No valid records found"

**Cause**: File has headers/summaries but no actual data rows

**Solution**:
* Remove "Total" rows at bottom
* Remove summary/calculation rows
* Keep only actual transaction data
* Ensure at least one data row exists

### Error: "Missing required columns"

**Cause**: Column names don't match expected format

**Solution**:
* Check column headers match requirements
* Common fixes:
  * "Quantity" → Rename to "Qty"
  * "Retail Amount" → Rename to "R_Amt"
  * "Wholesale Amount" → Rename to "W_Amt"
  * "Item" → Rename to "Item_Name"

### Error: "Period detection failed"

**Cause**: Filename doesn't contain recognizable date information

**Solution**:
* Rename file with clear period info
* Examples:
  * `"sales_data.xlsx"` ❌ → `"Nov 2025.xlsx"` ✅
  * `"grocery.xlsx"` ❌ → `"2024.xlsx"` ✅
  * `"report.xlsx"` ❌ → `"Jan to Sep 2025.xlsx"` ✅

### Error: "Data for period already exists"

**Cause**: You've already uploaded data for this time period

**Solution**:
1. Go to "Upload History" tab
2. Find the previous upload for this period
3. Click red "UNDO" button to remove it
4. Return and upload new file

### Error: "File too large"

**Cause**: Excel file exceeds 50MB limit

**Solution**:
* Split into smaller files by month
* Remove unnecessary columns
* Save as .xlsx not .xls (better compression)
* Delete any embedded images/charts

---

# 8. Tab 6: Upload History

**Purpose**: Track all data uploads and manage them

## What You'll See

### Upload History Table

Each row represents one upload showing:
* **Upload Date & Time** - When you uploaded (e.g., "Dec 12, 2025 10:30 AM")
* **Filename** - Original Excel file name
* **Period Covered** - Formatted period (e.g., "Jan-Sep 2025", "Nov 2025")
* **Records Count** - Number of items uploaded
* **Upload Type** - "Daily" or "Historical"
* **Status** - ✅ Success or ❌ Failed
* **Actions** - UNDO button (red)

### Table Features

**Sorting**: Click any column header to sort

**Search**: Type to filter by filename or period

**Pagination**: Choose 10, 25, 50, or 100 rows per page

**Recent First**: Newest uploads appear at top

## Understanding Upload Types

**Daily Upload**:
* Single day's data
* Typically smaller (10-500 records)
* Uploaded via Daily Upload Dashboard or Daily Sales Report
* Period: Specific date

**Historical Upload**:
* Multi-day, monthly, or yearly data
* Typically larger (100-5000+ records)
* Uploaded via Bulk Data Upload tab
* Period: Month, year, or range

## Using the UNDO Feature

### When to UNDO

**Valid Reasons**:
* Uploaded wrong file by mistake
* Period detected incorrectly
* Duplicate data uploaded
* File had errors discovered later
* Need to replace with corrected data

### How to UNDO

**Step 1**: Find the upload in history table
* Use search if many uploads
* Check period and date to confirm correct one

**Step 2**: Click red "UNDO" button
* Located in Actions column
* Only appears for successful uploads

**Step 3**: Confirm deletion
* Popup appears: "Delete this upload and all its records?"
* **Warning**: "This action cannot be reversed!"
* Click "Yes, Delete" to proceed

**Step 4**: Wait for completion
* Progress indicator appears
* System removes all records from this upload
* Success message: "Upload undone successfully"

**Step 5**: Verify removal
* Check Dashboard - numbers should decrease
* Check Analytics - data should reflect removal
* Check Database View - records gone

### Important UNDO Notes

⚠️ **Cannot Be Reversed**: Once undone, data is permanently deleted
⚠️ **Affects Everything**: Removes data from all tabs and reports
⚠️ **No Partial Undo**: Removes entire upload, not individual records
✅ **Safe**: Only affects data from that specific upload

### After UNDO

**Re-Upload Corrected Data**:
1. Fix your Excel file
2. Go to Bulk Data Upload tab
3. Upload corrected file
4. Verify period and records count
5. Confirm upload

**Dashboard Updates**:
* All metrics recalculate automatically
* Charts refresh with correct data
* Period may disappear if it was only upload for that period

---

# 9. Tab 7: Database View

**Purpose**: View, search, filter, and export all sales records

## One-Time Migration Tool (NEW!)

### ⚡ Period Migration Section
Located at the top in a **yellow warning box**

**What it does**:
* Fixes period formats from old versions
* Updates "2025-01" → "2025-01-09" (Jan-Sep range)
* Corrects any misformatted periods in database

**When to use**:
* After deploying latest update
* If periods showing incorrectly
* If uploaded before smart detection feature
* **Only need to run ONCE!**

**How to use**:
1. You'll see yellow box: "⚡ One-Time Migration"
2. Read description
3. Click orange "Run Migration" button
4. Confirm when prompted
5. Wait for success message
6. View automatically refreshes

**What happens**:
* Scans database for old period formats
* Updates to new format
* Shows count: "Updated 2,530 records"
* Period names now consistent everywhere

**After migration**: You can hide this section or developer will remove it in next update

## Viewing Records

### Main Data Table

**Columns Displayed** (scroll horizontally to see all):
* Item Code
* Item Name
* Product Group
* Quantity Sold
* Net Quantity
* Wholesale Rate
* Retail Rate
* Wholesale Amount
* Retail Amount
* Profit
* Closing Stock
* Opening Balance
* Net Tax
* Period
* Upload Date

### Display Modes

**Regular View** (Default):
* Shows individual sales records
* One row per transaction
* All fields visible
* Can see daily variations

**Aggregated View** (Toggle switch):
* Groups records by item
* Sums quantities and amounts
* Shows **latest rates** (most recent prices)
* Displays all periods item appears in
* Calculates averages for stocks
* Shows record count per item

**When to use Aggregated**:
* Get item totals across all time
* See overall performance per product
* Export summary instead of details
* Faster loading for large datasets

## Filter Controls

### Group Filter
* Dropdown selector
* Choose "All Groups" or specific group
* Filters table instantly

### Period Filter (Consistent Formatting!)
**Dropdown shows**:
* All Periods
* Current Period (Dec 2025)
* Nov 2025
* Oct 2025
* Jan-Sep 2025
* 2024, 2023, 2022

**Functionality**:
* Same formatted periods as Analytics and Reports
* Select to filter table to that period
* Works with both Regular and Aggregated views

### GP Index No Filter
* Text input box
* Enter specific item code
* Shows only that item's records

### Search Box
* Type item name or any text
* Searches across all visible columns
* Real-time filtering as you type

## Sorting Records

**Click any column header to sort**:
* First click: Ascending (A-Z, 0-9, oldest-newest)
* Second click: Descending (Z-A, 9-0, newest-oldest)
* Third click: Remove sort

**Useful sorts**:
* By Profit (descending) → See most profitable sales
* By Quantity (descending) → See largest transactions
* By Period (descending) → See recent data first

## Pagination

**Controls at bottom**:
* **Rows per page**: Choose 10, 25, 50, or 100
* **Page navigation**: First, Previous, Next, Last buttons
* **Page indicator**: "Showing 1-50 of 21,605"

**For large exports**: Set to 100 rows, review data quality before exporting all

## Exporting Data

### Export Button
Large button: "Export" with download icon

### Export Process (Chunked for Large Datasets)

**Step 1**: Click "Export" button

**Step 2**: System fetches all records in chunks
* Backend limit: 500 records per request
* Frontend automatically handles pagination
* Progress toast shows: "Fetching records... 500/8,894"

**Step 3**: Watch progress
* Updates every chunk: "1,000/8,894", "1,500/8,894"
* Can take 10-60 seconds for 20K+ records

**Step 4**: Download triggers automatically
* File: `database-export-2025-12-12.csv`
* Opens save dialog
* Complete dataset in one file

### Export Data Quality

**For Regular View**:
* All individual transaction records
* Actual rates from each sale

**For Aggregated View**:
* One row per item
* Totals for quantities and amounts
* **Latest rates** (most recent prices, not averages!)
* All periods concatenated

### CSV Format
* Headers in first row
* Data properly quoted
* Indian number format NOT applied (use numbers)
* Dates in readable format
* Opens in Excel, Google Sheets, any CSV tool

## Record Counts

**Top of page shows**:
* "Total Records: 21,605" - Complete database count
* "Showing: 8,894" - After filters applied

**Why different?**
* Total = Everything ever uploaded
* Showing = Current filters/period/group selection

---

# 10. Report Generation System

**Purpose**: Create comprehensive multi-period analysis reports

## Accessing Report Generation

**Location**: Top-right corner of every page

**Two Buttons**:
* 🟢 **Excel Report** - Download .xlsx file
* 🔵 **PDF Report** - Download .pdf file

## Multi-Select Period Feature (Key Feature!)

### Opening the Report Dialog

**Step 1**: Click "Excel Report" or "PDF Report" button

**Step 2**: Dialog appears with:
* Format selector (already set based on button clicked)
* Period selection area with checkboxes
* "Select All / Deselect All" toggle button
* Selection counter: "X periods selected"
* Generate Report button

### Understanding Period Selection

**All periods shown**:
* Current Period (Dec 2025)
* Nov 2025
* Oct 2025
* Jan-Sep 2025
* 2024
* 2023
* 2022

**Default behavior**:
* **ALL periods pre-selected** when dialog opens
* Generates complete historical analysis
* Can deselect periods you don't want

### Selecting Periods

**Select All / Deselect All**:
* Toggle button at top-right
* One click selects everything
* Second click deselects everything

**Individual Selection**:
* Check/uncheck specific period checkboxes
* Select any combination you want
* Examples:
  * Just "Nov 2025" - Single month analysis
  * "Nov 2025" + "Oct 2025" - Two-month comparison
  * "2024" + "2023" - Year-over-year analysis
  * "Jan-Sep 2025" + "2024" - Range + year comparison

**Selection Counter**:
* Shows "5 periods selected" 
* Updates in real-time as you check/uncheck
* Helps confirm your selection

### Validation

**Cannot generate without selection**:
* If no periods checked: Error toast
* Message: "Please select at least one period for the report"
* Must select at least one period to proceed

## Report Titles

**System automatically creates descriptive titles**:

**Single Period**:
* `"URC 101 Report - Nov 2025"`

**Two Periods**:
* `"URC 101 Report - Nov 2025 & 2024"`

**Multiple Periods (3-5)**:
* `"URC 101 Report - Nov 2025, Oct 2025, 2024"`

**Many Periods (6+)**:
* `"URC 101 Report - Nov 2025 to 2022 (5 periods)"`

**All Periods**:
* `"URC 101 Report - All Periods"`

**This title appears**:
* On every page/sheet of report
* In file name
* In report header

## Generating the Report

### Final Steps

**Step 1**: Verify period selection
* Check counter shows correct count
* Review which periods are checked

**Step 2**: Click "Generate Report" button
* Loading toast appears: "Generating report..."
* Takes 5-30 seconds depending on data size

**Step 3**: Download triggers
* Success toast: "Report downloaded successfully"
* File saves to your Downloads folder
* Dialog closes automatically

### Filename Format

**Excel Files**:
* Single: `URC101-Report-2025-11.xlsx`
* Multiple: `URC101-Report-5Periods.xlsx`
* All: `URC101-Report-AllPeriods.xlsx`

**PDF Files**:
* Same pattern with .pdf extension

## Use Cases for Multi-Period Reports

### Monthly Performance Review
**Select**: Current month only
**Purpose**: Detailed analysis of this month
**Use for**: Daily management decisions

### Quarter Analysis
**Select**: Last 3 months (Oct + Nov + Dec)
**Purpose**: Quarterly business review
**Use for**: Board meetings, strategy planning

### Year-over-Year Comparison
**Select**: 2024 + 2023 + 2022
**Purpose**: Multi-year trends
**Use for**: Annual planning, growth analysis

### Seasonal Analysis
**Select**: Same months across years (e.g., all November periods)
**Purpose**: Understand seasonal patterns
**Use for**: Inventory planning for next year

### Complete History
**Select**: All periods
**Purpose**: Comprehensive business overview
**Use for**: New management, audits, benchmarking

---

# 11. Understanding Reports

## Excel Report Structure (7 Sheets)

### Sheet 1: Executive Summary

**Purpose**: High-level business overview

**Key Metrics**:
* **Total Revenue** - All sales in selected periods
* **Total Profit** - Earnings after costs
* **Profit Margin** - Profitability percentage
* **Total Items Sold** - Unit count
* **Average Transaction Value**
* **Number of Unique Items** - SKU count

**Formatted as**: Indian Number System
* Example: ₹23,92,58,751.93 (23 crores, 92 lakhs...)

**Period Information**: Shown in title - "Report for Nov 2025 & 2024"

**Use for**: Quick health check, executive presentations

### Sheet 2: ABC Analysis

**Purpose**: Inventory classification by value

**Sections**:
1. **Category A (Fast Moving)** - Green section
   * Lists top performers
   * Shows % contribution
   * Individual item details
   
2. **Category B (Medium Moving)** - Blue section
   * Medium performers
   * Moderate contribution
   
3. **Category C (Slow Moving)** - Red section
   * Bottom performers
   * Minimal contribution

**Recommendations Included**:
* Stock level suggestions
* Ordering priorities
* Shelf placement guidance

**Use for**: Inventory optimization, space allocation

### Sheet 3: Capital Blocking Analysis

**Purpose**: Identify money tied up in inventory

**Columns**:
* Item Code & Name
* Product Group  
* Closing Stock (units)
* Wholesale Rate
* **Capital Blocked** (Stock × Rate)
* Days to Sell
* Risk Level
* Recommendation

**Sorted by**: Risk level (Critical first), then capital amount

**Top 50 Items** shown

**Use for**: Cash flow management, clearance planning

### Sheet 4: Group Performance

**Purpose**: Category-wise breakdown

**For each product group**:
* Total Revenue
* Total Profit
* Profit Margin %
* Item Count
* Rank by revenue

**Chart included**: Bar chart comparing groups

**Use for**: Category management, buyer negotiations

### Sheet 5: Top Performers

**Purpose**: Best-selling items analysis

**Top 20 items shown with**:
* Rank (1-20)
* Item Code & Name
* **Product Group** (Group VI, Group III, etc.)
* Quantity Sold
* Revenue Generated
* Profit Earned
* Margin %
* Days Supply (stock / daily sales)

**Calculations**:
* Margin = (Profit / Revenue) × 100
* Daily Sales = Total Sold / Days in Period

**Use for**: Promotional planning, prime placement decisions

### Sheet 6: Items to Liquidate

**Purpose**: Identify items to clear

**Bottom 20 items shown with**:
* Item details
* Total sold (very low)
* Closing stock (usually high)
* **Capital Blocked**
* Urgency Rating
* Action Required

**Categories**:
* **Urgent** - Clear within 7 days
* **Plan Clearance** - Clear within 30 days
* **Monitor** - Watch for 90 days

**Use for**: Clearance sales, return negotiations, space recovery

### Sheet 7: Smart Recommendations

**Purpose**: Actionable insights and strategies

**Four Main Sections**:

**A. Immediate Actions (0-7 days)**:
* Specific items to clear
* Discount percentages suggested
* Expected recovery amounts
* Stock reduction targets

**B. 3-Month Strategy**:
* Category-wise procurement adjustments
* SKU optimization (add/remove)
* Pricing recommendations
* Margin improvement opportunities

**C. Product Group Optimization**:
* Which groups to expand
* Which groups to reduce
* Cross-category opportunities
* Supplier negotiation points

**D. Profit Maximization Plan**:
* High-margin items to promote
* Low-margin items to discontinue
* Pricing adjustments needed
* Expected profit increase

**All recommendations include**:
* Specific numbers/targets
* Expected financial impact
* Timeline for implementation
* Priority level

**Use for**: Action planning, team assignments, progress tracking

## PDF Report

**Same 7 sections as Excel** but formatted for:
* Professional presentation
* Printing
* Client/board sharing
* Email distribution

**Formatting features**:
* Color-coded sections (same colors as Excel)
* Professional header on each page
* **Period shown prominently in title**
* Indian Number System (Rs notation)
* Clean tables and charts
* Page numbers
* Generated timestamp

**File size**: Typically 2-5 MB depending on data volume

## Number Formats in Reports

**Indian Number System Used**:
* ₹1,00,000 = 1 lakh
* ₹10,00,000 = 10 lakhs
* ₹1,00,00,000 = 1 crore
* ₹23,92,58,751.93 = 23 crores, 92 lakhs...

**Decimal Places**:
* Currency: 2 decimals (₹123.45)
* Percentages: 2 decimals (45.67%)
* Quantities: Whole numbers (1,234 units)

## When to Generate Reports

**Daily**: Not necessary - use Dashboard instead

**Weekly**: 
* For management review meetings
* Select current month only
* Quick check on progress

**Monthly**:
* End of month - Select completed month
* Review performance
* Plan next month
* Share with team

**Quarterly**:
* Select last 3 months
* Board presentations
* Strategy sessions
* Trend analysis

**Annually**:
* Select full year
* Annual reports
* Tax planning
* Audits

**Ad-Hoc**:
* When investigating issues
* For specific period analysis
* Before making big decisions
* When requested by management

---

# 12. Best Practices

## Daily Tasks

### For Data Entry Clerk (15 minutes/day)

**Morning (5 minutes)**:
1. Check if yesterday's upload successful
2. Verify Dashboard shows expected numbers
3. Review any failed upload notifications

**Evening (10 minutes)**:
1. **Upload Today's Sales**
   * Use "Upload Today's Data" button on Dashboard
   * Or go to Daily Sales Report tab
   * Verify file has today's transactions
   
2. **Generate Financial Report** (if required)
   * Enter liquor sales manually
   * Verify grocery sales auto-filled
   * Leave stock value blank for auto-calc
   * Download PDF
   
3. **Quick Verification**
   * Check Dashboard updated
   * Verify record count increased
   * Note any alerts or warnings

### For Store Manager (10 minutes/day)

**Morning Routine**:
1. Open Dashboard
2. Check Daily Sales Trend chart
3. Review yesterday's performance
4. Note any inventory alerts
5. Check top sellers changed

**Actions**:
* Red alerts (dead inventory) → Immediate clearance
* Orange alerts (slow moving) → Reduce orders
* Yellow alerts (high cost poor) → Monitor/promote

## Weekly Tasks

### For Inventory Manager (30 minutes/week)

**Every Monday Morning**:

1. **Analytics Review** (15 min)
   * Go to Detailed Analytics tab
   * Select "Current Period"
   * Review all 4 sub-sections
   * Note any concerning trends

2. **Capital Blocking Check** (10 min)
   * Focus on CRITICAL items
   * Plan clearance actions
   * Set weekly clearance target
   * Assign responsibility

3. **Inventory Health** (5 min)
   * Count dead inventory items
   * Track week-over-week change
   * Celebrate reductions!

**Every Friday**:
* Generate weekly report (last 7 days if possible, or current month)
* Review with team
* Plan next week's focus

### For Store Manager (1 hour/week)

**Week Start**:
* Review Dashboard fully
* Check all metrics vs targets
* Set weekly goals

**Week End**:
* Generate Excel report for current month
* Analyze Sheet 7 (Smart Recommendations)
* Prioritize actions for next week
* Brief team on priorities

## Monthly Tasks

### For Inventory Manager (2-3 hours/month)

**First Week of Month** (After previous month ends):

1. **Upload Complete Month** (if not daily uploaded)
   * Prepare final month file
   * Name correctly: "Nov 2025.xlsx"
   * Upload via Bulk Data Upload
   * Verify period shows correctly

2. **ABC Analysis Deep Dive**
   * Generate report with last month only
   * Compare Category counts month-over-month
   * Identify items moving between categories
   * Adjust stocking policies

3. **Capital Blocking Assessment**
   * Focus on HIGH and CRITICAL items
   * Calculate total capital trapped
   * Set monthly clearance targets
   * Track progress on previous month's targets

4. **Performance Review**
   * Select last 3 months in report
   * Identify trends
   * Find consistent winners and losers
   * Make category adjustments

### For Business Owner/Manager (3-4 hours/month)

**Monthly Business Review**:

1. **Generate Comprehensive Report**
   * Select last 3 months
   * Excel + PDF formats
   * Review all 7 sheets thoroughly

2. **Financial Analysis**
   * Review profit margins by group
   * Compare to previous months
   * Check if targets met

3. **Strategic Decisions**
   * Based on Sheet 7 recommendations
   * Approve clearances
   * Adjust buying patterns
   * Set next month's targets

4. **Team Communication**
   * Share relevant sections with team
   * Assign action items
   * Set deadlines
   * Schedule follow-up

## Quarterly Tasks (4-6 hours/quarter)

**For Management Team**:

1. **Trend Analysis**
   * Generate report with all 3 months of quarter
   * Compare with previous quarter
   * Identify seasonal patterns
   * Year-over-year comparison

2. **Category Performance Review**
   * Evaluate each product group
   * Decide on expansions/reductions
   * Renegotiate with suppliers
   * Consider new categories

3. **Forecasting**
   * Generate forecasts for next quarter
   * All product groups
   * Plan inventory levels
   * Budget for purchases

4. **Strategic Planning**
   * Review Sheet 7 recommendations from last 3 months
   * Assess implementation success
   * Adjust strategies
   * Set quarterly goals

## Best Practices by Role

### Data Entry Clerk

**Do**:
✅ Upload daily without fail
✅ Use clear, consistent file names
✅ Verify uploads successful
✅ Report errors immediately
✅ Keep backup of Excel files
✅ Check period shows correctly

**Don't**:
❌ Skip days - causes gaps in analysis
❌ Upload same data twice
❌ Ignore error messages
❌ Modify Excel files after upload
❌ Delete uploads without manager approval

### Inventory Manager

**Do**:
✅ Review analytics weekly minimum
✅ Act on CRITICAL capital blocking immediately
✅ Track clearance progress
✅ Use forecasting for ordering
✅ Focus on profit, not just sales
✅ Document decisions and results

**Don't**:
❌ Ignore dead inventory
❌ Keep slow movers "just in case"
❌ Order without checking analytics
❌ Focus only on popular items
❌ Neglect Category C items

### Store Manager/Owner

**Do**:
✅ Check Dashboard daily
✅ Generate monthly reports
✅ Review recommendations seriously
✅ Share insights with team
✅ Set measurable targets
✅ Track improvements over time
✅ Celebrate successes

**Don't**:
❌ Make decisions without data
❌ Ignore recommendations repeatedly
❌ Hoard slow-moving stock
❌ Avoid difficult decisions
❌ Forget to follow up on action items

---

# 13. Troubleshooting

## Common Issues and Solutions

### Period-Related Issues

#### Issue: Periods showing as "Jan 2025" instead of "Jan-Sep 2025"

**Cause**: Data uploaded before smart period detection feature

**Solution**:
1. Go to Database View tab
2. Look for yellow **"⚡ One-Time Migration"** box at top
3. Click orange "Run Migration" button
4. Confirm when prompted
5. Wait for success message
6. Refresh browser

**Result**: All "2025-01" records updated to "2025-01-09", displays as "Jan-Sep 2025"

#### Issue: Different periods in Analytics vs Reports

**Cause**: Using outdated version

**Solution**:
* Ensure latest version deployed
* Run migration in Database View
* Clear browser cache (Ctrl+Shift+R)
* Periods will now match everywhere

#### Issue: Period not detected from filename

**Cause**: Filename unclear or unsupported format

**Solution**:
* Rename file with clear period info:
  * Good: "Jan to Sep 2025.xlsx" ✅
  * Good: "Nov 2025.xlsx" ✅
  * Bad: "grocery_data.xlsx" ❌
  * Bad: "report_final.xlsx" ❌
* Re-upload with better filename

### Analytics Issues

#### Issue: No data in Detailed Analytics for specific period

**Cause**: Period filter using old format

**Solution**:
* Run migration in Database View first
* Then select period from Analytics dropdown
* Should show "Nov 2025", not "2025-11"
* Data will load correctly

#### Issue: Export buttons not working in Analytics

**Cause**: Fixed in latest version

**Solution**:
* Update to latest code
* Export now includes period parameter
* Test with "Export" button in each sub-section

### Database View Issues

#### Issue: Export shows zeros in rate columns

**Cause**: Aggregated view doesn't have individual rates

**Solution**:
* Latest version calculates latest rates automatically
* For aggregated view: Shows most recent rate per item
* For regular view: Shows actual transaction rates
* Update to latest version for fix

#### Issue: Export fails with "Failed to fetch records"

**Cause**: Too many records, old version couldn't handle

**Solution**:
* Latest version uses chunked export
* Automatically fetches in batches of 500
* Watch progress toast: "Fetching records... X/Y"
* Works for 20K+ records

### Upload Issues

#### Issue: "Data for period already exists"

**Cause**: You've uploaded this period before

**Solution**:
1. Check if data is correct already
2. If need to replace:
   * Go to Upload History tab
   * Find previous upload
   * Click red UNDO button
   * Re-upload new file

#### Issue: Upload shows "0 records processed"

**Cause**: File has no valid data rows

**Solution**:
* Check file has data rows (not just headers)
* Remove "Total" rows and summaries
* Remove blank rows
* Ensure required columns present
* Re-save and upload

#### Issue: Wrong profit calculations

**Cause**: Missing W_Amt or R_Amt columns

**Solution**:
* Profit = R_Amt - W_Amt
* Both columns required
* Check your Excel has both
* Verify numbers are correct
* Don't use formulas - use values

### Report Issues

#### Issue: Cannot generate report - no periods selected

**Cause**: All checkboxes unchecked

**Solution**:
* At least one period must be selected
* Click "Select All" button
* Or check specific periods you want
* Then click Generate

#### Issue: Report title shows wrong period

**Cause**: Using old version

**Solution**:
* Update to latest code
* Report titles now show formatted periods
* Example: "Report - Nov 2025 & 2024"

### Dashboard Issues

#### Issue: Stock value not updating

**Cause**: Dashboard cache or missing financial report

**Solution**:
* Click refresh button (🔄) next to stock value
* Or generate new financial report
* Dashboard updates automatically after report generation

#### Issue: Daily Sales Trend chart empty

**Cause**: No data for current quarter

**Solution**:
* Chart shows last 3 months
* Upload current month's data
* If new system, upload at least current month
* Chart will populate as data accumulates

### General Issues

#### Issue: "Failed to load analytics data"

**Cause**: Backend connection issue or period mismatch

**Solution**:
* Refresh browser (F5)
* Check internet connection
* Run migration if just updated
* Clear browser cache if persists

#### Issue: Graphs not showing

**Cause**: Browser compatibility or cache

**Solution**:
* Use Chrome, Firefox, or Edge (recommended)
* Clear browser cache: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
* Disable browser extensions temporarily
* Try incognito/private mode

#### Issue: Slow performance

**Cause**: Large dataset or browser issues

**Solution**:
* Close other browser tabs
* Clear browser cache
* Use pagination in Database View
* Use filters to reduce data shown
* Export for offline analysis if needed

### Getting Help

**Technical Issues**:
* Clear browser cache first
* Note exact error message
* Screenshot the issue
* Contact system administrator

**Data Questions**:
* Check this handbook first
* Review sample data in Database View
* Compare with Excel file uploaded
* Ask manager or data team

**Training Needs**:
* Review relevant handbook section
* Practice with test data
* Shadow experienced user
* Request hands-on training session

---

## Glossary of Terms

**ABC Analysis**: Inventory classification method where top 20% items = 80% revenue

**Aggregated View**: Database view showing totals per item instead of individual transactions

**Capital Blocking**: Money tied up in unsold inventory (Stock × Rate)

**Chunked Export**: Fetching large datasets in small batches (500 records at a time)

**Current Period**: Auto-detected ongoing month (e.g., "Current Period (Dec 2025)")

**Data Period**: Time range for sales data (month, year, or range)

**Dead Inventory**: Stock with zero sales in period

**Group**: Product category (Group I, II, III, IV, VI)

**Latest Rate**: Most recent price for an item (not average)

**Multi-Select Period**: Choosing multiple time periods for combined report

**Period Range**: Data spanning multiple months (e.g., "Jan-Sep 2025")

**SKU**: Stock Keeping Unit - unique item identifier

**Slow Moving**: Items selling < 5 units per month

**Smart Period Detection**: Automatic recognition of dates from filenames

---

## Version History

**Version 3.3 (Current - December 2025)**
* ✅ Comprehensive documentation rewrite
* ✅ Accurate tab order (7 tabs)
* ✅ All latest features documented
* ✅ Latest rates in aggregated export
* ✅ Chunked export for large datasets
* ✅ Period consistency across all features

**Version 3.2 (December 2025)**
* ✅ Smart period detection from filenames
* ✅ Multi-select period report generation
* ✅ Period consistency improvements
* ✅ Migration tool in Database View
* ✅ Fixed group data display
* ✅ Updated tab names

**Version 3.1 (November 2025)**
* Financial report editing and deletion
* Indian Number System formatting
* Enhanced recommendations

**Version 3.0 (October 2025)**
* Analytics tab with 4 sub-sections
* ABC analysis and capital blocking
* Inventory health tracking

---

## End of User Handbook

**Version 3.3** | Updated: December 2025 | URC 101 Grocery Sales Analytics

**Complete Guide** - All Features - Latest Version - Accurate Tab Order

For support or questions, contact your system administrator.
