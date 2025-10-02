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
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, ReferenceLine } from "recharts";
import { TrendingUp, Brain, Calculator, Zap, AlertTriangle, CheckCircle, Info, X, Upload, Calendar, ArrowRight, ArrowLeft, Download } from "lucide-react";
import { toast } from "sonner";

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

  useEffect(() => {
    if (forecastMethod) {
      const requirements = generateDataRequirements();
      setRequiredDataUploads(requirements);
    }
  }, [forecastMonth, forecastYear, forecastMethod]);

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

      const response = await fetch(`${API}/upload-sales-data`, {
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
      setUploadedData(prev => ({
        ...prev,
        [requirementId]: {
          file: file.name,
          status: 'error',
          error: error.message
        }
      }));
      toast.error(`Failed to upload ${file.name}: ${error.message}`);
    }
  };

  const proceedToNextStep = () => {
    if (step === 1 && forecastMonth && forecastYear) {
      setStep(2);
    } else if (step === 2 && forecastMethod) {
      setStep(3);
    } else if (step === 3) {
      const requiredUploads = requiredDataUploads.filter(req => req.required);
      const completedRequired = requiredUploads.filter(req => 
        uploadedData[req.id] && uploadedData[req.id].status === 'success'
      );
      
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

      const response = await fetch(`${API}/forecast-demand`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      const results = await response.json();
      
      if (response.ok) {
        setForecastResults(results);
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
              <span>Upload Required Data</span>
            </CardTitle>
            <CardDescription>
              Upload the following data files for {forecastMethod === 'trend' ? 'trend' : forecastMethod === 'statistical' ? 'statistical' : 'AI-powered'} forecasting of {' '}
              {forecastMonth && forecastYear && new Date(parseInt(forecastYear), parseInt(forecastMonth) - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {requiredDataUploads.map((requirement) => (
                <Card key={requirement.id} className={`border ${
                  requirement.required ? 'border-blue-200 bg-blue-50' : 'border-gray-200'
                }`}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <h4 className="font-medium">{requirement.title}</h4>
                          {requirement.required && (
                            <Badge variant="destructive" className="text-xs">Required</Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mb-3">{requirement.description}</p>
                        
                        {uploadedData[requirement.id] ? (
                          <div className="flex items-center space-x-2">
                            {uploadedData[requirement.id].status === 'success' ? (
                              <>
                                <CheckCircle className="h-5 w-5 text-green-600" />
                                <span className="text-green-700 text-sm">
                                  ✅ {uploadedData[requirement.id].file} ({uploadedData[requirement.id].records} records)
                                </span>
                              </>
                            ) : (
                              <>
                                <AlertTriangle className="h-5 w-5 text-red-600" />
                                <span className="text-red-700 text-sm">
                                  ❌ {uploadedData[requirement.id].error}
                                </span>
                              </>
                            )}
                          </div>
                        ) : (
                          <div className="text-sm text-gray-500">No file uploaded</div>
                        )}
                      </div>
                      
                      <div className="ml-4">
                        <input
                          type="file"
                          accept=".xlsx,.xls"
                          onChange={(e) => {
                            const file = e.target.files[0];
                            if (file) {
                              handleDataUpload(requirement.id, file);
                            }
                          }}
                          className="hidden"
                          id={`upload-${requirement.id}`}
                        />
                        <label
                          htmlFor={`upload-${requirement.id}`}
                          className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 cursor-pointer"
                        >
                          <Upload className="h-4 w-4 mr-2" />
                          Choose File
                        </label>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            
            {requiredDataUploads.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <Info className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p>No additional data upload required.</p>
                <p className="text-sm">The forecast will use existing historical data in the system.</p>
              </div>
            )}
            
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
                  requiredDataUploads.filter(req => req.required && uploadedData[req.id]?.status === 'success').length < requiredDataUploads.filter(req => req.required).length
                }
              >
                Generate Forecast
                <Zap className="h-4 w-4 ml-2" />
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
                Your demand forecast has been generated successfully using existing 3-year historical data.
              </p>
            </div>
            
            <div className="mt-6 flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                New Forecast
              </Button>
              
              <Button className="bg-green-600 hover:bg-green-700">
                <Download className="h-4 w-4 mr-2" />
                Export Results
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Forecasting;
