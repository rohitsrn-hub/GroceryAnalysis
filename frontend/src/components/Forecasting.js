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
import { TrendingUp, Brain, Calculator, Zap, AlertTriangle, CheckCircle, Info, X, Upload } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Forecasting = () => {
  const [forecastMethod, setForecastMethod] = useState('trend');
  const [forecastMonths, setForecastMonths] = useState(4);
  const [selectedItems, setSelectedItems] = useState([]);
  const [forecastResults, setForecastResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [additionalInputs, setAdditionalInputs] = useState('');
  const [fastestItems, setFastestItems] = useState([]);
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [forecastRequirements, setForecastRequirements] = useState(null);
  const [showRequirements, setShowRequirements] = useState(true);

  useEffect(() => {
    fetchFastestItems();
    fetchForecastRequirements();
  }, []);

  const fetchForecastRequirements = async () => {
    try {
      const response = await fetch(`${API}/forecast-requirements`);
      const data = await response.json();
      setForecastRequirements(data);
    } catch (error) {
      console.error("Error fetching forecast requirements:", error);
    }
  };

  const fetchFastestItems = async () => {
    try {
      const response = await fetch(`${API}/fastest-selling-items?limit=50`);
      const data = await response.json();
      setFastestItems(data);
    } catch (error) {
      console.error("Error fetching items:", error);
    }
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
      {/* Forecast Data Requirements */}
      {showRequirements && forecastRequirements && (
        <Card className="border-2 border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center space-x-2">
                <Info className="h-5 w-5 text-blue-600" />
                <span>Data Requirements for Accurate Forecasting</span>
              </span>
              <Button variant="ghost" size="sm" onClick={() => setShowRequirements(false)}>
                <X className="h-4 w-4" />
              </Button>
            </CardTitle>
            <CardDescription>
              Current data status and requirements for different forecast accuracy levels
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Current Data Status */}
              <div className="space-y-4">
                <h4 className="font-semibold text-blue-800">Current Data Status</h4>
                <div className="p-4 bg-white rounded-lg border border-blue-200">
                  <div className="space-y-2">
                    <p className="text-sm">
                      <strong>Available Periods:</strong> {forecastRequirements.current_data_status.available_periods.join(", ")}
                    </p>
                    <p className="text-sm">
                      <strong>Total Records:</strong> {forecastRequirements.current_data_status.total_records.toLocaleString()}
                    </p>
                    <p className="text-sm">
                      <strong>Items with Sales:</strong> {forecastRequirements.current_data_status.sample_items}
                    </p>
                  </div>
                </div>

                {/* Accuracy Levels */}
                <h4 className="font-semibold text-blue-800">Forecast Accuracy Levels</h4>
                <div className="space-y-3">
                  {Object.entries(forecastRequirements.forecast_accuracy_levels).map(([key, level]) => (
                    <div key={key} className="p-3 bg-white rounded-lg border border-blue-200">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-blue-800 capitalize">
                          {key.replace("_", " ")}
                        </span>
                        <Badge className={
                          level.accuracy.includes("85-90") ? "bg-green-600" :
                          level.accuracy.includes("80-85") ? "bg-blue-600" :
                          "bg-orange-600"
                        }>
                          {level.accuracy}
                        </Badge>
                      </div>
                      <p className="text-sm text-blue-700">{level.description}</p>
                      <p className="text-xs text-blue-600 mt-1">
                        <strong>Data needed:</strong> {level.data_needed}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Data Upload Instructions */}
              <div className="space-y-4">
                <h4 className="font-semibold text-blue-800">Upload Additional Data</h4>
                <div className="p-4 bg-white rounded-lg border border-blue-200">
                  <h5 className="font-medium mb-2">For Seasonal Analysis:</h5>
                  <p className="text-sm text-blue-700 mb-3">
                    {forecastRequirements.required_for_seasonal_forecast.description}
                  </p>
                  
                  <h5 className="font-medium mb-2">For Year-over-Year Comparison:</h5>
                  <p className="text-sm text-blue-700 mb-2">
                    {forecastRequirements.required_for_yearly_comparison.description}
                  </p>
                  <div className="flex space-x-2 mb-3">
                    {forecastRequirements.required_for_yearly_comparison.years_needed.map((year) => (
                      <Badge key={year} variant="outline">{year} Data</Badge>
                    ))}
                  </div>

                  <div className="mt-4 p-3 bg-blue-100 rounded-lg">
                    <h6 className="font-medium text-blue-800 mb-2">Upload Format Requirements:</h6>
                    <ul className="text-sm text-blue-700 space-y-1">
                      <li>• <strong>Format:</strong> {forecastRequirements.data_upload_instructions.format}</li>
                      <li>• <strong>Naming:</strong> {forecastRequirements.data_upload_instructions.naming_convention}</li>
                      <li>• <strong>Required Columns:</strong> {forecastRequirements.data_upload_instructions.required_columns.join(", ")}</li>
                    </ul>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="space-y-2">
                  <Button 
                    className="w-full" 
                    onClick={() => {
                      // Navigate to upload tab
                      window.location.hash = "#upload";
                    }}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Upload Historical Data
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={() => setShowRequirements(false)}
                  >
                    Continue with Current Data
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Forecasting Setup */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Brain className="h-6 w-6" />
            <span>Demand Forecasting</span>
          </CardTitle>
          <CardDescription>
            Generate demand forecasts using multiple methodologies with real-time parameter selection
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Method Selection */}
            <div className="space-y-4">
              <Label className="text-base font-semibold">Forecasting Method</Label>
              <div className="space-y-3">
                {['trend', 'statistical', 'ai'].map((method) => {
                  const info = getMethodDescription(method);
                  return (
                    <div 
                      key={method}
                      className={`p-4 border rounded-lg cursor-pointer transition-all ${
                        forecastMethod === method 
                          ? `border-${info.color}-500 bg-${info.color}-50` 
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => setForecastMethod(method)}
                    >
                      <div className="flex items-center space-x-2 mb-2">
                        {getMethodIcon(method)}
                        <span className="font-medium">{info.title}</span>
                        {forecastMethod === method && (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{info.description}</p>
                      <Badge 
                        variant="outline" 
                        className={`mt-2 text-${info.color}-700 border-${info.color}-300`}
                      >
                        Accuracy: {info.accuracy}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Parameters */}
            <div className="space-y-4">
              <Label className="text-base font-semibold">Parameters</Label>
              
              <div className="space-y-3">
                <div>
                  <Label htmlFor="forecast-months">Forecast Period (Months)</Label>
                  <Select value={forecastMonths.toString()} onValueChange={(value) => setForecastMonths(parseInt(value))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select months" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 Month</SelectItem>
                      <SelectItem value="2">2 Months</SelectItem>
                      <SelectItem value="3">3 Months</SelectItem>
                      <SelectItem value="4">4 Months (Recommended)</SelectItem>
                      <SelectItem value="6">6 Months</SelectItem>
                      <SelectItem value="12">12 Months</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="current-month">Current Month</Label>
                  <Select value={currentMonth.toString()} onValueChange={(value) => setCurrentMonth(parseInt(value))}>
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

                <div>
                  <Label htmlFor="item-selection">Specific Items (Optional)</Label>
                  <Select value="all" onValueChange={() => {}}>  {/* Simplified for demo */}
                    <SelectTrigger>
                      <SelectValue placeholder="All items" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Items</SelectItem>
                      <SelectItem value="top-10">Top 10 Items</SelectItem>
                      <SelectItem value="custom">Custom Selection</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Method-Specific Inputs */}
            <div className="space-y-4">
              <Label className="text-base font-semibold">Method Requirements</Label>
              
              <div className={`p-4 border rounded-lg bg-${methodInfo.color}-50 border-${methodInfo.color}-200`}>
                <h4 className="font-medium mb-2 flex items-center space-x-2">
                  <Info className="h-4 w-4" />
                  <span>{methodInfo.title}</span>
                </h4>
                <ul className="text-sm space-y-1">
                  {methodInfo.requirements.map((req, index) => (
                    <li key={index} className="flex items-center space-x-2">
                      <CheckCircle className="h-3 w-3 text-green-600" />
                      <span>{req}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {(forecastMethod === 'ai' || forecastMethod === 'statistical') && (
                <div>
                  <Label htmlFor="additional-inputs">
                    {forecastMethod === 'ai' ? 'Market Context & External Factors' : 'Seasonal Adjustments'}
                  </Label>
                  <Textarea
                    id="additional-inputs"
                    value={additionalInputs}
                    onChange={(e) => setAdditionalInputs(e.target.value)}
                    placeholder={
                      forecastMethod === 'ai' 
                        ? "Enter market trends, economic factors, competitor actions, seasonal events, etc."
                        : "Enter seasonal patterns, holiday effects, promotional periods, etc."
                    }
                    className="mt-1"
                    rows={4}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Generate Forecast Button */}
          <div className="mt-6 pt-6 border-t">
            <Button 
              onClick={handleForecast} 
              disabled={loading}
              className="w-full md:w-auto"
              size="lg"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Generating {methodInfo.title}...
                </>
              ) : (
                <>
                  {getMethodIcon(forecastMethod)}
                  <span className="ml-2">Generate Forecast</span>
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Forecast Results */}
      {loading && (
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      )}

      {forecastResults && !loading && (
        <Tabs defaultValue="charts" className="space-y-6">
          <TabsList>
            <TabsTrigger value="charts">Forecast Charts</TabsTrigger>
            <TabsTrigger value="table">Detailed Results</TabsTrigger>
            <TabsTrigger value="alerts">Stock Alerts</TabsTrigger>
          </TabsList>

          {/* Charts Tab */}
          <TabsContent value="charts" className="space-y-6">
            {chartData.map((item, index) => (
              <Card key={index}>
                <CardHeader>
                  <CardTitle className="text-lg">{item.item_name}</CardTitle>
                  <CardDescription>
                    Historical vs Forecasted Sales ({methodInfo.title})
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={item.data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="period" />
                      <YAxis />
                      <Tooltip />
                      <Line 
                        type="monotone" 
                        dataKey="actual" 
                        stroke="#3B82F6" 
                        strokeWidth={2}
                        dot={{ fill: '#3B82F6', r: 4 }}
                        connectNulls={false}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="forecast" 
                        stroke="#EF4444" 
                        strokeDasharray="5 5"
                        strokeWidth={2}
                        dot={{ fill: '#EF4444', r: 4 }}
                        connectNulls={false}
                      />
                      <ReferenceLine 
                        x="Forecast 1" 
                        stroke="#6B7280" 
                        strokeDasharray="2 2" 
                        label="Forecast Start"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* Table Tab */}
          <TabsContent value="table">
            <Card>
              <CardHeader>
                <CardTitle>Forecast Results Summary</CardTitle>
                <CardDescription>
                  Detailed forecast data for all analyzed items
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-3 font-semibold">Item</th>
                        <th className="text-left p-3 font-semibold">Method</th>
                        <th className="text-left p-3 font-semibold">Historical Avg</th>
                        <th className="text-left p-3 font-semibold">Forecast Avg</th>
                        <th className="text-left p-3 font-semibold">Trend</th>
                        <th className="text-left p-3 font-semibold">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecastResults?.forecasts?.map((forecast, index) => {
                        const historicalAvg = forecast.historical_sales.reduce((sum, val) => sum + val, 0) / forecast.historical_sales.length;
                        const forecastAvg = forecast.forecasted_sales.reduce((sum, val) => sum + val, 0) / forecast.forecasted_sales.length;
                        const trendDirection = forecastAvg > historicalAvg ? 'increasing' : 'decreasing';
                        
                        return (
                          <tr key={index} className="border-b hover:bg-gray-50">
                            <td className="p-3">
                              <div>
                                <p className="font-medium text-sm">{forecast.item_name}</p>
                                <p className="text-xs text-gray-500">{forecast.pluno}</p>
                              </div>
                            </td>
                            <td className="p-3">
                              <Badge variant="outline">{forecast.method}</Badge>
                            </td>
                            <td className="p-3">{historicalAvg.toFixed(1)}</td>
                            <td className="p-3 font-medium">{forecastAvg.toFixed(1)}</td>
                            <td className="p-3">
                              <Badge 
                                variant={trendDirection === 'increasing' ? 'default' : 'secondary'}
                                className={trendDirection === 'increasing' ? 'bg-green-600' : 'bg-red-600'}
                              >
                                {trendDirection === 'increasing' ? '↗️ Growing' : '↘️ Declining'}
                              </Badge>
                            </td>
                            <td className="p-3">
                              {forecastAvg > historicalAvg * 1.2 ? (
                                <Badge className="bg-orange-600">Increase Stock</Badge>
                              ) : forecastAvg < historicalAvg * 0.8 ? (
                                <Badge variant="secondary">Reduce Orders</Badge>
                              ) : (
                                <Badge variant="outline">Maintain</Badge>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Alerts Tab */}
          <TabsContent value="alerts">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <AlertTriangle className="h-5 w-5 text-orange-600" />
                    <span>Stock Alerts & Recommendations</span>
                  </CardTitle>
                  <CardDescription>
                    Items requiring immediate attention based on forecast analysis
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {getStockAlerts().length > 0 ? (
                      getStockAlerts().map((item, index) => {
                        const avgForecast = item.forecasted_sales.reduce((sum, val) => sum + val, 0) / item.forecasted_sales.length;
                        const currentStock = item.historical_sales[item.historical_sales.length - 1] || 0;
                        
                        return (
                          <div key={index} className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="font-medium text-orange-900">{item.item_name}</p>
                                <p className="text-sm text-orange-700 mt-1">
                                  Current Stock Level: {currentStock} units
                                </p>
                                <p className="text-sm text-orange-700">
                                  Forecasted Monthly Demand: {avgForecast.toFixed(1)} units
                                </p>
                                <p className="text-sm text-orange-600 mt-2">
                                  ⚠️ Stock may run out before {new Date(2024, currentMonth + forecastMonths - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                                </p>
                              </div>
                              <Badge className="bg-orange-600">Stock Alert</Badge>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="text-center p-8">
                        <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
                        <p className="text-lg font-medium text-green-800">No Stock Alerts</p>
                        <p className="text-green-600">All items appear to have adequate stock levels based on the forecast</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Forecast Summary */}
              <Card>
                <CardHeader>
                  <CardTitle>Forecast Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <p className="text-sm text-blue-600">Total Items Analyzed</p>
                      <p className="text-2xl font-bold text-blue-800">
                        {forecastResults?.forecasts?.length || 0}
                      </p>
                    </div>
                    
                    <div className="p-4 bg-green-50 rounded-lg">
                      <p className="text-sm text-green-600">Growing Demand Items</p>
                      <p className="text-2xl font-bold text-green-800">
                        {forecastResults?.forecasts?.filter(f => {
                          const historicalAvg = f.historical_sales.reduce((sum, val) => sum + val, 0) / f.historical_sales.length;
                          const forecastAvg = f.forecasted_sales.reduce((sum, val) => sum + val, 0) / f.forecasted_sales.length;
                          return forecastAvg > historicalAvg;
                        }).length || 0}
                      </p>
                    </div>
                    
                    <div className="p-4 bg-orange-50 rounded-lg">
                      <p className="text-sm text-orange-600">Requires Attention</p>
                      <p className="text-2xl font-bold text-orange-800">
                        {getStockAlerts().length}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      )}

      {/* Method Information */}
      {!forecastResults && !loading && (
        <Card>
          <CardHeader>
            <CardTitle>How It Works</CardTitle>
            <CardDescription>Understanding the different forecasting methodologies</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {['trend', 'statistical', 'ai'].map((method) => {
                const info = getMethodDescription(method);
                return (
                  <div key={method} className="p-4 border rounded-lg">
                    <div className="flex items-center space-x-2 mb-3">
                      {getMethodIcon(method)}
                      <h3 className="font-semibold">{info.title}</h3>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{info.description}</p>
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-gray-700">Requirements:</p>
                      {info.requirements.map((req, index) => (
                        <p key={index} className="text-xs text-gray-600 flex items-center space-x-1">
                          <span>•</span>
                          <span>{req}</span>
                        </p>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Forecasting;
