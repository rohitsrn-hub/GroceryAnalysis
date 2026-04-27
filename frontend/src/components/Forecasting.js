import { apiFetch } from '../utils/api';
import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import { Textarea } from "./ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Skeleton } from "./ui/skeleton";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, ReferenceLine, PieChart, Pie, Cell, Legend } from "recharts";
import { TrendingUp, Brain, Calculator, Zap, AlertTriangle, CheckCircle, Info, X, Upload, Calendar, ArrowRight, ArrowLeft, Download } from "lucide-react";
import { toast } from "sonner";
import { ErrorDialog } from "./ui/error-dialog";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Forecasting = () => {
  const [step, setStep] = useState(1); // 1: Date Selection, 2: Method Selection, 3: Data Upload, 4: Results
  const [forecastMonth, setForecastMonth] = useState('');
  const [forecastYear, setForecastYear] = useState('');
  const [forecastMethod, setForecastMethod] = useState('');
  const [requiredDataUploads, setRequiredDataUploads] = useState([]);
  const [uploadedData, setUploadedData] = useState({});
  const [forecastResults, setForecastResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [additionalInputs, setAdditionalInputs] = useState('');
  const [fastestItems, setFastestItems] = useState([]);
  const [showRequirements, setShowRequirements] = useState(false);
  const [forecastMonths, setForecastMonths] = useState(4);
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [selectedItems, setSelectedItems] = useState([]);
  const [errorDialog, setErrorDialog] = useState({ open: false, title: "", message: "", details: "" });
  const [dataAvailability, setDataAvailability] = useState({});
  const [checkingAvailability, setCheckingAvailability] = useState(false);
  const [monthlySummaries, setMonthlySummaries] = useState([]);
  const [showUploadOverride, setShowUploadOverride] = useState({});

  useEffect(() => {
    // Fetch monthly summaries on component mount
    fetchMonthlySummaries();
  }, []);

  useEffect(() => {
    if (forecastMethod) {
      const requirements = generateDataRequirements();
      setRequiredDataUploads(requirements);
      // Check data availability when requirements change
      checkDataAvailability(requirements);
    }
  }, [forecastMonth, forecastYear, forecastMethod, monthlySummaries]);

  const fetchMonthlySummaries = async () => {
    try {
      const response = await apiFetch(`${API}/monthly-summaries`);
      if (response.ok) {
        const data = await response.json();
        setMonthlySummaries(data.summaries || []);
      }
    } catch (error) {
      console.error("Error fetching monthly summaries:", error);
    }
  };

  const checkDataAvailability = async (requirements) => {
    if (!requirements || requirements.length === 0) return;
    
    setCheckingAvailability(true);
    try {
      // Check both monthly summaries and raw data
      const availability = {};
      
      for (const req of requirements) {
        if (!req.period || req.period === 'contextual' || req.period === 'current' || req.period.startsWith('quarter_')) {
          continue;
        }
        
        // First check if we have a monthly summary for this period
        const summary = monthlySummaries.find(s => s.period === req.period);
        
        if (summary) {
          availability[req.period] = {
            available: true,
            source: 'monthly_summary',
            item_count: summary.item_count,
            total_revenue: summary.total_revenue,
            display_name: summary.display_name,
            data_source: summary.source === 'user_uploaded' ? 'User Uploaded' : 'Auto Generated',
            created_at: summary.created_at
          };
        } else {
          // Fall back to checking raw sales records
          try {
            const response = await apiFetch(`${API}/check-data-availability`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify([req.period])
            });
            
            if (response.ok) {
              const result = await response.json();
              if (result.availability && result.availability[req.period]) {
                availability[req.period] = {
                  ...result.availability[req.period],
                  source: 'raw_data'
                };
              }
            }
          } catch (e) {
            // Ignore individual period check errors
          }
        }
      }
      
      setDataAvailability(availability);
    } catch (error) {
      console.error("Error checking data availability:", error);
    } finally {
      setCheckingAvailability(false);
    }
  };

  const generateDataRequirements = () => {
    if (!forecastMonth || !forecastYear || !forecastMethod) return [];

    const currentDate = new Date();
    const currentMonth = currentDate.getMonth() + 1;
    const currentYear = currentDate.getFullYear();
    const targetMonth = parseInt(forecastMonth);
    const targetYear = parseInt(forecastYear);

    const requirements = [];

    if (forecastMethod === 'trend') {
      // For trend analysis: need last 3 months of data
      for (let i = 1; i <= 3; i++) {
        let month = currentMonth - i;
        let year = currentYear;
        
        if (month <= 0) {
          month += 12;
          year -= 1;
        }

        requirements.push({
          id: `trend_month_${i}`,
          title: `${new Date(year, month - 1).toLocaleDateString('en-US', { month: 'long' })} ${year} Sales Data`,
          description: `Upload sales data for ${new Date(year, month - 1).toLocaleDateString('en-US', { month: 'long' })} ${year}`,
          type: 'monthly_sales',
          period: `${year}-${month.toString().padStart(2, '0')}`,
          required: true
        });
      }
    } else if (forecastMethod === 'statistical') {
      // For statistical: last 3 months + same month from previous years
      // Last 3 months
      for (let i = 1; i <= 3; i++) {
        let month = currentMonth - i;
        let year = currentYear;
        
        if (month <= 0) {
          month += 12;
          year -= 1;
        }

        requirements.push({
          id: `stat_recent_${i}`,
          title: `${new Date(year, month - 1).toLocaleDateString('en-US', { month: 'long' })} ${year} Sales Data`,
          description: `Recent sales data for trend analysis`,
          type: 'monthly_sales',
          period: `${year}-${month.toString().padStart(2, '0')}`,
          required: true
        });
      }

      // Same month from previous years for seasonal analysis
      const monthName = new Date(targetYear, targetMonth - 1).toLocaleDateString('en-US', { month: 'long' });
      for (let yearBack = 1; yearBack <= 3; yearBack++) {
        const pastYear = targetYear - yearBack;
        requirements.push({
          id: `stat_seasonal_${yearBack}`,
          title: `${monthName} ${pastYear} Sales Data`,
          description: `Historical data for seasonal pattern analysis`,
          type: 'seasonal_data',
          period: `${pastYear}-${targetMonth.toString().padStart(2, '0')}`,
          required: true
        });
      }

      // Optional: Quarter data around target month
      requirements.push({
        id: 'stat_quarterly',
        title: `Quarterly Data Around ${monthName}`,
        description: 'Optional: Upload sales data for months before/after target month for better seasonal analysis',
        type: 'quarterly_data',
        period: `quarter_${targetMonth}`,
        required: false
      });

    } else if (forecastMethod === 'ai') {
      // For AI: comprehensive data requirements
      
      // Recent trend data (6 months)
      for (let i = 1; i <= 6; i++) {
        let month = currentMonth - i;
        let year = currentYear;
        
        if (month <= 0) {
          month += 12;
          year -= 1;
        }

        requirements.push({
          id: `ai_recent_${i}`,
          title: `${new Date(year, month - 1).toLocaleDateString('en-US', { month: 'long' })} ${year} Sales Data`,
          description: `Recent sales data for AI pattern recognition`,
          type: 'monthly_sales',
          period: `${year}-${month.toString().padStart(2, '0')}`,
          required: i <= 3 // Only first 3 are required
        });
      }

      // Historical seasonal data
      const monthName = new Date(targetYear, targetMonth - 1).toLocaleDateString('en-US', { month: 'long' });
      for (let yearBack = 1; yearBack <= 5; yearBack++) {
        const pastYear = targetYear - yearBack;
        requirements.push({
          id: `ai_seasonal_${yearBack}`,
          title: `${monthName} ${pastYear} Complete Data`,
          description: `Historical ${monthName} data for deep learning patterns`,
          type: 'seasonal_data',
          period: `${pastYear}-${targetMonth.toString().padStart(2, '0')}`,
          required: yearBack <= 3
        });
      }

      // Market context data
      requirements.push({
        id: 'ai_market_context',
        title: 'Market Context & External Factors',
        description: 'Upload market research, competitor analysis, economic indicators, promotional calendars',
        type: 'market_data',
        period: 'contextual',
        required: false
      });

      // Inventory levels
      requirements.push({
        id: 'ai_inventory',
        title: 'Current Inventory Levels',
        description: 'Upload current stock levels, procurement pipeline, supplier data',
        type: 'inventory_data',
        period: 'current',
        required: true
      });
    }

    return requirements;
  };

  const handleDataUpload = async (requirementId, file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('upload_source', 'forecast');  // Mark as forecast data

      const response = await apiFetch(`${API}/upload-sales-data`, {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setUploadedData(prev => ({
          ...prev,
          [requirementId]: {
            file: file.name,
            status: 'success',
            records: result.records_count
          }
        }));
        toast.success(`Successfully uploaded ${file.name}`);
      } else {
        throw new Error(result.detail || 'Upload failed');
      }
    } catch (error) {
      const errorMessage = error.message;
      
      setUploadedData(prev => ({
        ...prev,
        [requirementId]: {
          file: file.name,
          status: 'error',
          error: errorMessage
        }
      }));
      
      // Show error in modal dialog
      setErrorDialog({
        open: true,
        title: `Failed to upload ${file.name}`,
        message: errorMessage,
        details: errorMessage.includes("No valid records found") 
          ? "The file was processed but contained no valid data rows. Common reasons:\n\n• Data format doesn't match requirements\n• Item names or product codes are missing\n• Rows were filtered due to data quality issues\n\nRefer to the required format below."
          : errorMessage.includes("Excel file format")
          ? "Cannot read the Excel file. Ensure:\n\n• File is valid .xlsx or .xls format\n• File is not corrupted\n• File is not password-protected"
          : "An error occurred while processing the file."
      });
    }
  };

  const proceedToNextStep = () => {
    if (step === 1 && forecastMonth && forecastYear) {
      // Validate that forecast date is not in the past
      const currentDate = new Date();
      const currentYear = currentDate.getFullYear();
      const currentMonth = currentDate.getMonth() + 1; // JavaScript months are 0-indexed
      
      const selectedYear = parseInt(forecastYear);
      const selectedMonth = parseInt(forecastMonth);
      
      if (selectedYear < currentYear || (selectedYear === currentYear && selectedMonth < currentMonth)) {
        setErrorDialog({
          open: true,
          title: "Invalid Forecast Period",
          message: `Cannot generate forecast for past period: ${new Date(selectedYear, selectedMonth - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}`,
          details: `Current period is ${new Date(currentYear, currentMonth - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}. You can only forecast for current or future months.\n\nPlease select a month that is equal to or later than the current month.`
        });
        return;
      }
      
      setStep(2);
    } else if (step === 2 && forecastMethod) {
      setStep(3);
    } else if (step === 3) {
      const requiredUploads = requiredDataUploads.filter(req => req.required);
      const completedRequired = requiredUploads.filter(req => {
        // Check if data is uploaded in current session OR already available in database
        const isUploaded = uploadedData[req.id] && uploadedData[req.id].status === 'success';
        const isAvailable = dataAvailability[req.period] && dataAvailability[req.period].available;
        return isUploaded || isAvailable;
      });
      
      if (completedRequired.length === requiredUploads.length || requiredUploads.length === 0) {
        handleForecast();
      } else {
        toast.error(`Please upload all required data files (${completedRequired.length}/${requiredUploads.length} completed)`);
      }
    }
  };

  const goBack = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleForecast = async () => {
    if (forecastMethod === 'ai' && !additionalInputs.trim()) {
      toast.error("Please provide additional market context for AI forecasting");
      return;
    }

    if (forecastMethod === 'statistical' && forecastMonths < 3) {
      toast.error("Statistical forecasting requires at least 3 months of forecast period");
      return;
    }

    try {
      setLoading(true);
      
      const requestBody = {
        method: forecastMethod,
        item_codes: selectedItems.length > 0 ? selectedItems : null,
        forecast_months: forecastMonths,
        additional_data: {
          market_context: additionalInputs,
          current_month: currentMonth,
          seasonal_adjustments: forecastMethod === 'statistical',
          trend_analysis: forecastMethod === 'trend'
        }
      };

      const response = await apiFetch(`${API}/forecast-demand`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      const results = await response.json();
      
      if (response.ok) {
        setForecastResults(results);
        setStep(4); // Move to results step
        toast.success(`Generated ${forecastMethod} forecast successfully`);
      } else {
        throw new Error(results.detail || 'Forecast generation failed');
      }
    } catch (error) {
      console.error("Error generating forecast:", error);
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const getMethodIcon = (method) => {
    switch (method) {
      case 'trend': return <TrendingUp className="h-4 w-4" />;
      case 'statistical': return <Calculator className="h-4 w-4" />;
      case 'ai': return <Brain className="h-4 w-4" />;
      default: return <Zap className="h-4 w-4" />;
    }
  };

  const getMethodDescription = (method) => {
    switch (method) {
      case 'trend':
        return {
          title: "Simple Trend Analysis",
          description: "Linear regression based on historical sales data trends",
          requirements: ["At least 2 data points", "Historical sales data"],
          accuracy: "Basic",
          color: "blue"
        };
      case 'statistical':
        return {
          title: "Statistical Forecasting",
          description: "Moving averages with seasonal adjustments and trend analysis",
          requirements: ["At least 3 months of data", "Seasonal pattern identification"],
          accuracy: "Moderate",
          color: "green"
        };
      case 'ai':
        return {
          title: "AI-Powered Forecasting",
          description: "Advanced machine learning with external market factors",
          requirements: ["Market context data", "External trend indicators", "Feature engineering"],
          accuracy: "High (when fully implemented)",
          color: "purple"
        };
      default:
        return { title: "", description: "", requirements: [], accuracy: "", color: "gray" };
    }
  };

  const methodInfo = getMethodDescription(forecastMethod);

  // Prepare chart data
  const chartData = forecastResults?.forecasts?.slice(0, 5).map(forecast => {
    const historicalData = forecast.historical_sales.map((value, index) => ({
      period: `Period ${index + 1}`,
      actual: value,
      type: 'historical'
    }));
    
    const forecastData = forecast.forecasted_sales.map((value, index) => ({
      period: `Forecast ${index + 1}`,
      forecast: value,
      type: 'forecast'
    }));
    
    return {
      item_name: forecast.item_name,
      data: [...historicalData, ...forecastData]
    };
  }) || [];

  const getStockAlerts = () => {
    if (!forecastResults?.forecasts) return [];
    
    return forecastResults.forecasts.filter(forecast => {
      const avgForecast = forecast.forecasted_sales.reduce((sum, val) => sum + val, 0) / forecast.forecasted_sales.length;
      // Assuming current stock is last historical value (simplified)
      const currentStock = forecast.historical_sales[forecast.historical_sales.length - 1] || 0;
      return currentStock < avgForecast * 0.5; // Alert if stock is less than 50% of forecasted demand
    }).slice(0, 10);
  };

  const handleExportResults = () => {
    if (!forecastResults || !forecastResults.forecasts) {
      toast.error("No forecast data to export");
      return;
    }

    try {
      // Create CSV content with detailed calculations
      const headers = [
        'Item Code',
        'Item Name',
        'Method',
        'Period 1 (Historical)',
        'Period 2 (Historical)',
        'Period 3 (Historical)',
        'Historical Average',
        'Period 1 (Forecast)',
        'Period 2 (Forecast)',
        'Period 3 (Forecast)',
        'Period 4 (Forecast)',
        'Forecast Average',
        'Trend Direction',
        'Growth Rate (%)',
        'Calculation Notes'
      ];

      const csvRows = [headers.join(',')];

      forecastResults.forecasts.forEach(forecast => {
        // Calculate growth rate
        const historicalAvg = forecast.historical_sales.reduce((sum, val) => sum + val, 0) / forecast.historical_sales.length;
        const forecastAvg = forecast.forecasted_sales.reduce((sum, val) => sum + val, 0) / forecast.forecasted_sales.length;
        const growthRate = historicalAvg > 0 ? (((forecastAvg - historicalAvg) / historicalAvg) * 100).toFixed(2) : 0;
        
        // Pad arrays to ensure consistent column count
        const hist = [...forecast.historical_sales, '', '', ''].slice(0, 3);
        const pred = [...forecast.forecasted_sales, '', '', '', ''].slice(0, 4);
        
        // Create calculation notes
        let calcNotes = '';
        if (forecast.method === 'trend' || forecastMethod === 'trend') {
          calcNotes = 'Linear regression on historical data';
        } else if (forecast.method === 'statistical' || forecastMethod === 'statistical') {
          calcNotes = `Moving average with seasonal factor: ${forecast.seasonal_factor?.toFixed(2) || 'N/A'}`;
        } else {
          calcNotes = 'AI-powered prediction';
        }

        const row = [
          `"${forecast.pluno || ''}"`,
          `"${forecast.item_name || ''}"`,
          `"${forecast.method || forecastMethod}"`,
          hist[0] || 0,
          hist[1] || 0,
          hist[2] || 0,
          historicalAvg.toFixed(2),
          pred[0] || 0,
          pred[1] || 0,
          pred[2] || 0,
          pred[3] || 0,
          forecastAvg.toFixed(2),
          `"${forecast.trend_direction || 'stable'}"`,
          growthRate,
          `"${calcNotes}"`
        ];

        csvRows.push(row.join(','));
      });

      // Add summary row
      csvRows.push('');
      csvRows.push(`"Total Items","${forecastResults.forecasts.length}","","","","","","","","","","","","",""`);
      csvRows.push(`"Forecast Method","${forecastMethod}","","","","","","","","","","","","",""`);
      csvRows.push(`"Forecast Period","${forecastMonth}-${forecastYear}","","","","","","","","","","","","",""`);
      csvRows.push(`"Generated On","${new Date().toLocaleString()}","","","","","","","","","","","","",""`);

      // Create blob and download
      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      
      link.setAttribute('href', url);
      link.setAttribute('download', `demand-forecast-${forecastMonth}-${forecastYear}-detailed.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success("Detailed forecast results exported successfully!");
    } catch (error) {
      console.error("Error exporting results:", error);
      toast.error("Failed to export results");
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress Indicator */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Demand Forecasting Wizard</h2>
            <Badge variant="outline" className="text-sm">
              Step {step} of 4
            </Badge>
          </div>
          
          <div className="flex items-center space-x-4">
            {[1, 2, 3, 4].map((stepNum) => (
              <div key={stepNum} className="flex items-center space-x-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step >= stepNum ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
                }`}>
                  {stepNum}
                </div>
                <span className={`text-sm ${
                  step >= stepNum ? 'text-blue-600 font-medium' : 'text-gray-500'
                }`}>
                  {stepNum === 1 ? 'Select Date' : 
                   stepNum === 2 ? 'Choose Method' : 
                   stepNum === 3 ? 'Upload Data' : 'Generate Forecast'}
                </span>
                {stepNum < 4 && <div className="w-8 h-px bg-gray-300" />}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Step 1: Date Selection */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Calendar className="h-5 w-5" />
              <span>Select Forecast Period</span>
            </CardTitle>
            <CardDescription>
              Choose the month and year for which you want to generate demand forecast
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <Label htmlFor="forecast-month">Select Month</Label>
                <Select value={forecastMonth} onValueChange={setForecastMonth}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select month" />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 12 }, (_, i) => (
                      <SelectItem key={i + 1} value={(i + 1).toString()}>
                        {new Date(2024, i).toLocaleDateString('en-US', { month: 'long' })}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-4">
                <Label htmlFor="forecast-year">Select Year</Label>
                <Select value={forecastYear} onValueChange={setForecastYear}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select year" />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 5 }, (_, i) => {
                      const year = new Date().getFullYear() + i;
                      return (
                        <SelectItem key={year} value={year.toString()}>
                          {year}
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {forecastMonth && forecastYear && (
              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-blue-800 font-medium">
                  Forecast Target: {new Date(parseInt(forecastYear), parseInt(forecastMonth) - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </p>
                <p className="text-blue-600 text-sm mt-1">
                  This will generate demand predictions for all product categories for the selected month.
                </p>
              </div>
            )}
            
            <div className="mt-6 flex justify-end">
              <Button 
                onClick={proceedToNextStep}
                disabled={!forecastMonth || !forecastYear}
                className="px-8"
              >
                Next: Choose Method
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Method Selection */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Brain className="h-5 w-5" />
              <span>Select Forecasting Method</span>
            </CardTitle>
            <CardDescription>
              Choose the forecasting approach based on your data availability and accuracy requirements
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  id: 'trend',
                  title: 'Simple Trend Analysis',
                  icon: TrendingUp,
                  accuracy: '70-75%',
                  description: 'Linear regression based on recent sales trends',
                  dataNeeded: '3 months of recent sales data',
                  bestFor: 'Quick forecasts, stable products',
                  color: 'blue'
                },
                {
                  id: 'statistical',
                  title: 'Statistical Forecasting',
                  icon: Calculator,
                  accuracy: '80-85%',
                  description: 'Seasonal patterns with moving averages',
                  dataNeeded: '3 recent months + historical seasonal data',
                  bestFor: 'Seasonal products, medium-term planning',
                  color: 'green'
                },
                {
                  id: 'ai',
                  title: 'AI-Powered Analysis',
                  icon: Brain,
                  accuracy: '85-90%',
                  description: 'Advanced ML with market context integration',
                  dataNeeded: 'Comprehensive historical + market data',
                  bestFor: 'Strategic planning, complex patterns',
                  color: 'purple'
                }
              ].map((method) => {
                const Icon = method.icon;
                const isSelected = forecastMethod === method.id;
                
                return (
                  <Card 
                    key={method.id}
                    className={`cursor-pointer transition-all ${
                      isSelected 
                        ? `border-2 border-${method.color}-500 bg-${method.color}-50 shadow-md` 
                        : 'border hover:border-gray-400 hover:shadow-sm'
                    }`}
                    onClick={() => setForecastMethod(method.id)}
                  >
                    <CardContent className="p-6">
                      <div className="flex items-center space-x-3 mb-4">
                        <div className={`p-2 rounded-lg ${
                          isSelected ? `bg-${method.color}-600` : 'bg-gray-100'
                        }`}>
                          <Icon className={`h-5 w-5 ${
                            isSelected ? 'text-white' : 'text-gray-600'
                          }`} />
                        </div>
                        <div>
                          <h3 className="font-semibold text-lg">{method.title}</h3>
                          <Badge className={`${
                            method.color === 'blue' ? 'bg-blue-600' :
                            method.color === 'green' ? 'bg-green-600' : 'bg-purple-600'
                          }`}>
                            {method.accuracy} Accuracy
                          </Badge>
                        </div>
                      </div>
                      
                      <p className="text-gray-700 text-sm mb-4">{method.description}</p>
                      
                      <div className="space-y-2">
                        <div className="text-xs">
                          <span className="font-medium text-gray-600">Data Required:</span>
                          <p className="text-gray-500">{method.dataNeeded}</p>
                        </div>
                        <div className="text-xs">
                          <span className="font-medium text-gray-600">Best For:</span>
                          <p className="text-gray-500">{method.bestFor}</p>
                        </div>
                      </div>
                      
                      {isSelected && (
                        <CheckCircle className="h-6 w-6 text-green-600 mt-4" />
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
            
            <div className="mt-6 flex justify-between">
              <Button variant="outline" onClick={goBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              
              <Button 
                onClick={proceedToNextStep}
                disabled={!forecastMethod}
                className="px-8"
              >
                Next: Upload Data
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Data Upload */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Upload className="h-5 w-5" />
              <span>Review Data & Override (Optional)</span>
            </CardTitle>
            <CardDescription>
              Review available monthly summaries for {forecastMethod === 'trend' ? 'trend' : forecastMethod === 'statistical' ? 'statistical' : 'AI-powered'} forecasting of {' '}
              {forecastMonth && forecastYear && new Date(parseInt(forecastYear), parseInt(forecastMonth) - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Monthly Summaries Status Banner */}
            <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
              <div className="flex items-start space-x-3">
                <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-800">About Monthly Summaries</h4>
                  <p className="text-sm text-blue-700 mt-1">
                    The system uses <strong>item-wise monthly summaries</strong> for accurate forecasting, not daily sales files.
                    These summaries are auto-generated when you upload daily data for a new month, or you can upload your own.
                  </p>
                  <p className="text-sm text-blue-600 mt-2">
                    <strong>Available summaries:</strong> {monthlySummaries.length} months | 
                    <button 
                      onClick={fetchMonthlySummaries}
                      className="ml-2 text-blue-700 underline hover:text-blue-900"
                    >
                      Refresh
                    </button>
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {requiredDataUploads.map((requirement) => {
                const availability = dataAvailability[requirement.period];
                const isAvailable = availability?.available;
                const isSummary = availability?.source === 'monthly_summary';
                const showOverride = showUploadOverride[requirement.id];
                
                return (
                <Card key={requirement.id} className={`border ${
                  isAvailable 
                    ? isSummary ? 'border-green-300 bg-green-50' : 'border-yellow-200 bg-yellow-50'
                    : requirement.required 
                    ? 'border-red-200 bg-red-50' 
                    : 'border-gray-200'
                }`}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2 flex-wrap gap-2">
                          <h4 className="font-medium">{requirement.title}</h4>
                          {isAvailable ? (
                            isSummary ? (
                              <Badge className="text-xs bg-green-600">Monthly Summary Available</Badge>
                            ) : (
                              <Badge className="text-xs bg-yellow-600">Raw Data Only</Badge>
                            )
                          ) : requirement.required ? (
                            <Badge variant="destructive" className="text-xs">Required - Not Found</Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs">Optional</Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mb-3">{requirement.description}</p>
                        
                        {isAvailable ? (
                          <div className="p-3 bg-white rounded-lg border border-green-300">
                            <div className="flex items-start space-x-2">
                              <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                              <div className="flex-1">
                                <p className="text-green-700 font-medium text-sm">
                                  ✅ {isSummary ? 'Monthly Summary' : 'Data'} available for {availability.display_name || requirement.period}
                                </p>
                                <div className="text-xs text-green-600 mt-1 space-y-0.5">
                                  {availability.item_count && (
                                    <p>• {availability.item_count.toLocaleString()} items summarized</p>
                                  )}
                                  {availability.total_revenue && (
                                    <p>• Total Revenue: ₹{(availability.total_revenue / 100000).toFixed(2)} Lakhs</p>
                                  )}
                                  {availability.data_source && (
                                    <p>• Source: {availability.data_source}</p>
                                  )}
                                  {availability.record_count && !isSummary && (
                                    <p>• {availability.record_count.toLocaleString()} raw records</p>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            {/* Override Option */}
                            <div className="mt-3 pt-3 border-t border-green-200">
                              <button
                                onClick={() => setShowUploadOverride(prev => ({...prev, [requirement.id]: !prev[requirement.id]}))}
                                className="text-xs text-green-700 hover:text-green-900 underline"
                              >
                                {showOverride ? 'Hide upload option' : 'Want to override with your own data?'}
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="p-3 bg-white rounded-lg border border-red-200">
                            <div className="flex items-start space-x-2">
                              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
                              <div>
                                <p className="text-red-700 font-medium text-sm">
                                  No monthly summary found for {requirement.period}
                                </p>
                                <p className="text-xs text-red-600 mt-1">
                                  {requirement.required 
                                    ? 'Please upload data for this period or generate a summary.'
                                    : 'Optional - forecast will proceed without this data.'}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {/* Upload Section (shown when not available or override requested) */}
                        {(!isAvailable || showOverride) && (
                          <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                            <p className="text-xs text-gray-600 mb-2">
                              <strong>Upload your own summary:</strong> Excel file with item-wise monthly totals
                            </p>
                            
                            {uploadedData[requirement.id] && (
                              <div className="mb-2 flex items-center space-x-2">
                                {uploadedData[requirement.id].status === 'success' ? (
                                  <>
                                    <CheckCircle className="h-4 w-4 text-green-600" />
                                    <span className="text-green-700 text-xs">
                                      Uploaded: {uploadedData[requirement.id].file} ({uploadedData[requirement.id].records} records)
                                    </span>
                                  </>
                                ) : (
                                  <>
                                    <AlertTriangle className="h-4 w-4 text-red-600" />
                                    <span className="text-red-700 text-xs">
                                      Error: {uploadedData[requirement.id].error}
                                    </span>
                                  </>
                                )}
                              </div>
                            )}
                            
                            <div className="flex items-center space-x-2">
                              <input
                                type="file"
                                accept=".xlsx,.xls"
                                onChange={(e) => {
                                  const file = e.target.files[0];
                                  if (file) {
                                    handleForecastDataUpload(requirement.id, file, requirement.period);
                                  }
                                }}
                                className="hidden"
                                id={`upload-${requirement.id}`}
                              />
                              <label
                                htmlFor={`upload-${requirement.id}`}
                                className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 cursor-pointer"
                              >
                                <Upload className="h-3 w-3 mr-1" />
                                Upload Summary File
                              </label>
                              {!isAvailable && (
                                <button
                                  onClick={() => handleGenerateSummary(requirement.period)}
                                  className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100"
                                >
                                  <Zap className="h-3 w-3 mr-1" />
                                  Auto-Generate
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )})}
            </div>
            
            {requiredDataUploads.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <Info className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p>No additional data upload required.</p>
                <p className="text-sm">The forecast will use existing monthly summaries in the system.</p>
              </div>
            )}
            
            {/* Summary of Data Status */}
            <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
              <h4 className="font-medium text-gray-800 mb-2">Data Status Summary</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {Object.values(dataAvailability).filter(a => a.available && a.source === 'monthly_summary').length}
                  </div>
                  <div className="text-gray-600">Monthly Summaries</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-600">
                    {Object.values(dataAvailability).filter(a => a.available && a.source !== 'monthly_summary').length}
                  </div>
                  <div className="text-gray-600">Raw Data Only</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {requiredDataUploads.filter(r => r.required && !dataAvailability[r.period]?.available).length}
                  </div>
                  <div className="text-gray-600">Missing Required</div>
                </div>
              </div>
            </div>
            
            <div className="mt-6 flex justify-between">
              <Button variant="outline" onClick={goBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              
              <Button 
                onClick={proceedToNextStep}
                className="px-8"
                disabled={
                  requiredDataUploads.filter(req => req.required).length > 0 &&
                  requiredDataUploads.filter(req => {
                    if (!req.required) return true;
                    const isUploaded = uploadedData[req.id]?.status === 'success';
                    const isAvailable = dataAvailability[req.period]?.available;
                    return isUploaded || isAvailable;
                  }).length < requiredDataUploads.filter(req => req.required).length
                }
              >
                {loading ? 'Generating...' : 'Generate Forecast'}
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Results */}
      {step === 4 && forecastResults && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span>Forecast Results</span>
            </CardTitle>
            <CardDescription>
              Generated demand forecast for {forecastMonth && forecastYear && new Date(parseInt(forecastYear), parseInt(forecastMonth) - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Forecast Complete!</h3>
              <p className="text-gray-600">
                Your demand forecast has been generated successfully using {forecastMethod} method.
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Generated {forecastResults?.forecasts?.length || 0} item forecasts
              </p>
            </div>
            
            {/* Forecast Results Table */}
            {forecastResults?.forecasts && forecastResults.forecasts.length > 0 && (
              <div className="mt-6">
                <h4 className="font-semibold text-lg mb-4">Forecast Results with Calculation Details</h4>
                <div className="overflow-x-auto border rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="text-left p-3 font-semibold">Item Code</th>
                        <th className="text-left p-3 font-semibold">Item Name</th>
                        <th className="text-left p-3 font-semibold">Historical Data</th>
                        <th className="text-left p-3 font-semibold">Hist. Avg</th>
                        <th className="text-left p-3 font-semibold">Forecasted Data</th>
                        <th className="text-left p-3 font-semibold">Forecast Avg</th>
                        <th className="text-left p-3 font-semibold">Growth</th>
                        <th className="text-left p-3 font-semibold">Trend</th>
                        <th className="text-left p-3 font-semibold">Pattern</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecastResults.forecasts.slice(0, 15).map((forecast, index) => {
                        const historicalAvg = (forecast.historical_sales.reduce((sum, val) => sum + val, 0) / forecast.historical_sales.length).toFixed(1);
                        const forecastedAvg = (forecast.forecasted_sales.reduce((sum, val) => sum + val, 0) / forecast.forecasted_sales.length).toFixed(1);
                        const growthRate = historicalAvg > 0 ? (((forecastedAvg - historicalAvg) / historicalAvg) * 100).toFixed(1) : 0;
                        const trend = forecast.trend_direction || 'stable';
                        
                        // Calculate demand pattern
                        const hist = forecast.historical_sales;
                        let pattern = 'Steady';
                        if (hist.length >= 2) {
                          const firstHalf = hist.slice(0, Math.floor(hist.length / 2)).reduce((a, b) => a + b, 0) / Math.floor(hist.length / 2);
                          const secondHalf = hist.slice(Math.floor(hist.length / 2)).reduce((a, b) => a + b, 0) / Math.ceil(hist.length / 2);
                          const change = ((secondHalf - firstHalf) / firstHalf) * 100;
                          
                          if (change > 20) pattern = 'Rising';
                          else if (change < -20) pattern = 'Falling';
                          else if (Math.max(...hist) / Math.min(...hist.filter(v => v > 0)) > 2) pattern = 'Volatile';
                          else pattern = 'Steady';
                        }
                        
                        return (
                          <tr key={index} className="border-b hover:bg-gray-50">
                            <td className="p-3 font-mono text-xs">{forecast.pluno || 'N/A'}</td>
                            <td className="p-3 text-xs">{forecast.item_name?.substring(0, 25) || 'N/A'}{forecast.item_name?.length > 25 ? '...' : ''}</td>
                            <td className="p-3 text-xs text-gray-600">
                              <div className="font-mono">{forecast.historical_sales.slice(0, 3).join(', ')}</div>
                            </td>
                            <td className="p-3 font-medium text-gray-700">{historicalAvg}</td>
                            <td className="p-3 text-xs text-blue-600">
                              <div className="font-mono">{forecast.forecasted_sales.slice(0, 4).join(', ')}</div>
                            </td>
                            <td className="p-3 font-medium text-blue-600">{forecastedAvg}</td>
                            <td className="p-3">
                              <span className={`font-medium ${
                                growthRate > 0 ? 'text-green-600' : 
                                growthRate < 0 ? 'text-red-600' : 'text-gray-600'
                              }`}>
                                {growthRate > 0 ? '+' : ''}{growthRate}%
                              </span>
                            </td>
                            <td className="p-3">
                              <Badge className={
                                trend === 'increasing' ? 'bg-green-600' :
                                trend === 'decreasing' ? 'bg-red-600' : 'bg-gray-600'
                              }>
                                {trend}
                              </Badge>
                            </td>
                            <td className="p-3">
                              <Badge variant="outline" className={
                                pattern === 'Rising' ? 'border-green-500 text-green-700' :
                                pattern === 'Falling' ? 'border-red-500 text-red-700' :
                                pattern === 'Volatile' ? 'border-orange-500 text-orange-700' :
                                'border-blue-500 text-blue-700'
                              }>
                                {pattern}
                              </Badge>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {forecastResults.forecasts.length > 15 && (
                  <p className="text-sm text-gray-500 mt-3 text-center">
                    Showing 15 of {forecastResults.forecasts.length} forecasts. Export to see all results with full calculation details.
                  </p>
                )}
                
                {/* Group-wise Demand Pie Chart */}
                <div className="mt-8">
                  <h4 className="font-semibold text-lg mb-4">Group-wise Demand Distribution</h4>
                  <div className="bg-gray-50 p-6 rounded-lg border">
                    {(() => {
                      // Calculate group-wise totals
                      const groupData = {};
                      forecastResults.forecasts.forEach(forecast => {
                        // Use product_group field directly (already set during upload)
                        let group = forecast.product_group || 'Unknown';
                        
                        // If still unknown, try to extract from pluno
                        if (group === 'Unknown' && forecast.pluno) {
                          const pluno = forecast.pluno.toString().toUpperCase();
                          if (pluno.startsWith('I/')) group = 'Group I';
                          else if (pluno.startsWith('II/')) group = 'Group II';
                          else if (pluno.startsWith('III/')) group = 'Group III';
                          else if (pluno.startsWith('IV/')) group = 'Group IV';
                          else if (pluno.startsWith('V/')) group = 'Group V';
                          else if (pluno.startsWith('VI/')) group = 'Group VI';
                        }
                        
                        const avgForecast = forecast.forecasted_sales.reduce((sum, val) => sum + val, 0) / forecast.forecasted_sales.length;
                        
                        if (!groupData[group]) {
                          groupData[group] = 0;
                        }
                        groupData[group] += avgForecast;
                      });
                      
                      // Convert to array for pie chart
                      const pieData = Object.entries(groupData).map(([name, value]) => ({
                        name,
                        value: parseFloat(value.toFixed(2)),
                        percentage: 0 // Will calculate below
                      }));
                      
                      // Calculate total and percentages
                      const total = pieData.reduce((sum, item) => sum + item.value, 0);
                      pieData.forEach(item => {
                        item.percentage = ((item.value / total) * 100).toFixed(1);
                      });
                      
                      // Filter out Unknown if it's very small (< 0.5%)
                      const filteredPieData = pieData.filter(item => {
                        if (item.name === 'Unknown' && parseFloat(item.percentage) < 0.5) {
                          return false;
                        }
                        return true;
                      });
                      
                      // Colors for groups
                      const COLORS = {
                        'Group I': '#3b82f6',
                        'Group II': '#10b981',
                        'Group III': '#f59e0b',
                        'Group IV': '#ef4444',
                        'Group V': '#ec4899',
                        'Group VI': '#8b5cf6',
                        'Unknown': '#6b7280'
                      };
                      
                      return (
                        <div className="flex flex-col lg:flex-row items-center gap-8">
                          <div className="w-full lg:w-1/2">
                            <ResponsiveContainer width="100%" height={300}>
                              <PieChart>
                                <Pie
                                  data={filteredPieData}
                                  cx="50%"
                                  cy="50%"
                                  labelLine={false}
                                  label={({ name, percentage }) => `${name}: ${percentage}%`}
                                  outerRadius={100}
                                  fill="#8884d8"
                                  dataKey="value"
                                >
                                  {filteredPieData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[entry.name] || COLORS['Unknown']} />
                                  ))}
                                </Pie>
                                <Tooltip 
                                  formatter={(value) => value.toFixed(2)}
                                  contentStyle={{ backgroundColor: 'white', border: '1px solid #ccc', borderRadius: '8px' }}
                                />
                                <Legend />
                              </PieChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="w-full lg:w-1/2 space-y-3">
                            <h5 className="font-semibold text-gray-900 mb-3">Demand Summary by Group:</h5>
                            {filteredPieData.sort((a, b) => b.value - a.value).map((item, index) => (
                              <div key={index} className="flex items-center justify-between p-3 bg-white rounded-lg border">
                                <div className="flex items-center gap-3">
                                  <div 
                                    className="w-4 h-4 rounded" 
                                    style={{ backgroundColor: COLORS[item.name] || COLORS['Unknown'] }}
                                  />
                                  <span className="font-medium">{item.name}</span>
                                </div>
                                <div className="text-right">
                                  <div className="font-bold text-blue-600">{item.value.toFixed(0)} units</div>
                                  <div className="text-sm text-gray-500">{item.percentage}%</div>
                                </div>
                              </div>
                            ))}
                            <div className="pt-3 border-t">
                              <div className="flex justify-between font-bold text-gray-900">
                                <span>Total Forecasted Demand:</span>
                                <span className="text-blue-600">{total.toFixed(0)} units</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
                
                {/* Calculation Method Explanation */}
                <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h5 className="font-semibold text-blue-900 mb-2 flex items-center">
                    <Info className="h-4 w-4 mr-2" />
                    How Forecasts Are Calculated
                  </h5>
                  <div className="text-sm text-blue-800 space-y-2">
                    {forecastMethod === 'trend' && (
                      <>
                        <p><strong>Method:</strong> Linear Trend Analysis</p>
                        <p><strong>Formula:</strong> Uses simple linear regression on historical data points to project future values</p>
                        <p><strong>Calculation:</strong> y = mx + b, where m is the slope (trend) and b is the intercept</p>
                        <p><strong>Best for:</strong> Items with consistent growth or decline patterns</p>
                      </>
                    )}
                    {forecastMethod === 'statistical' && (
                      <>
                        <p><strong>Method:</strong> Statistical Forecasting with Moving Averages</p>
                        <p><strong>Formula:</strong> Moving Average × Seasonal Factor</p>
                        <p><strong>Calculation:</strong> Average of last 3 months adjusted for seasonal patterns</p>
                        <p><strong>Best for:</strong> Items with seasonal variations</p>
                      </>
                    )}
                    {forecastMethod === 'ai' && (
                      <>
                        <p><strong>Method:</strong> AI-Powered Forecasting</p>
                        <p><strong>Approach:</strong> Machine learning models considering multiple factors</p>
                        <p><strong>Factors:</strong> Historical trends, seasonal patterns, market context</p>
                        <p><strong>Best for:</strong> Complex patterns requiring advanced analysis</p>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            <div className="mt-6 flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                New Forecast
              </Button>
              
              <Button 
                className="bg-green-600 hover:bg-green-700"
                onClick={handleExportResults}
              >
                <Download className="h-4 w-4 mr-2" />
                Export Results
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Error Dialog */}
      <ErrorDialog
        open={errorDialog.open}
        onOpenChange={(open) => setErrorDialog({ ...errorDialog, open })}
        title={errorDialog.title}
        message={errorDialog.message}
        details={errorDialog.details}
      />
    </div>
  );
};

export default Forecasting;
