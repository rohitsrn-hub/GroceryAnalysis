import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Calendar, BarChart3, CheckSquare } from 'lucide-react';
import { formatIndianNumber, formatTableNumber } from '../utils/numberUtils';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Color palette for different periods
const PERIOD_COLORS = [
  '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6', 
  '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1',
  '#14B8A6', '#A855F7'
];

const SalesTrendsChart = () => {
  const [viewMode, setViewMode] = useState('last3'); // 'last3', 'last12', 'single', 'compare'
  const [availablePeriods, setAvailablePeriods] = useState([]);
  const [selectedPeriods, setSelectedPeriods] = useState([]);
  const [singlePeriod, setSinglePeriod] = useState('');
  const [trendData, setTrendData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showPeriodSelector, setShowPeriodSelector] = useState(false);

  useEffect(() => {
    fetchAvailablePeriods();
  }, []);

  useEffect(() => {
    // Only fetch trend data when periods are available
    if (availablePeriods.length > 0) {
      fetchTrendData();
    }
  }, [viewMode, selectedPeriods, singlePeriod, availablePeriods]);

  const fetchAvailablePeriods = async () => {
    try {
      const response = await fetch(`${API}/available-data-periods`);
      if (response.ok) {
        const data = await response.json();
        // Get periods from periods_detailed which has value/label format
        const allPeriods = data.periods_detailed || [];
        // Filter to only include monthly periods (format YYYY-MM)
        const monthlyPeriods = allPeriods.filter(p => p.value && p.value.match(/^\d{4}-\d{2}$/));
        setAvailablePeriods(monthlyPeriods);
        
        // Set default single period to most recent
        if (monthlyPeriods.length > 0) {
          setSinglePeriod(monthlyPeriods[0].value);  // First is most recent
        }
      }
    } catch (error) {
      console.error('Error fetching periods:', error);
    }
  };

  const fetchTrendData = async () => {
    try {
      setLoading(true);
      let periods = [];

      if (viewMode === 'last3') {
        // Get last 3 monthly periods
        periods = availablePeriods.slice(-3).map(p => p.value);
      } else if (viewMode === 'last12') {
        // Get last 12 monthly periods
        periods = availablePeriods.slice(-12).map(p => p.value);
      } else if (viewMode === 'single' && singlePeriod) {
        periods = [singlePeriod];
      } else if (viewMode === 'compare' && selectedPeriods.length > 0) {
        periods = selectedPeriods;
      }

      if (periods.length === 0) {
        setTrendData(null);
        setLoading(false);
        return;
      }

      // Fetch data for each period
      const periodDataPromises = periods.map(async (period) => {
        const response = await fetch(`${API}/daily-sales-trend-by-period?period=${period}`);
        if (response.ok) {
          return response.json();
        }
        return null;
      });

      const results = await Promise.all(periodDataPromises);
      
      // Filter out failed requests and format data
      const formattedData = results
        .filter(r => r && r.data && r.data.length > 0)
        .map((result, index) => ({
          period: result.period,
          periodLabel: result.period_label,
          color: PERIOD_COLORS[index % PERIOD_COLORS.length],
          data: result.data,
          totalSales: result.total_sales || 0,
          avgDailySales: result.avg_daily_sales || 0,
          daysTracked: result.days_tracked || 0
        }));

      setTrendData(formattedData);
    } catch (error) {
      console.error('Error fetching trend data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodToggle = (periodValue) => {
    setSelectedPeriods(prev => {
      if (prev.includes(periodValue)) {
        return prev.filter(p => p !== periodValue);
      } else {
        // Limit to 6 periods for comparison
        if (prev.length >= 6) {
          return prev;
        }
        return [...prev, periodValue];
      }
    });
  };

  // Calculate total stats
  const totalStats = useMemo(() => {
    if (!trendData || trendData.length === 0) return { totalSales: 0, periodsCompared: 0 };
    
    return {
      totalSales: trendData.reduce((sum, p) => sum + (p.totalSales || 0), 0),
      periodsCompared: trendData.length
    };
  }, [trendData]);

  // Transform data for the chart - align all periods by day number
  const chartData = useMemo(() => {
    if (!trendData || trendData.length === 0) return [];

    // Create data points for days 1-31
    const days = Array.from({ length: 31 }, (_, i) => i + 1);
    
    return days.map(day => {
      const point = { day };
      trendData.forEach(period => {
        const dayData = period.data.find(d => d.day === day);
        point[period.period] = dayData ? dayData.sales : null;
      });
      return point;
    });
  }, [trendData]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              <span>Daily Sales Trends</span>
            </CardTitle>
            <CardDescription>
              Track sales patterns over time across periods
            </CardDescription>
          </div>
          
          {/* View Mode Buttons */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={viewMode === 'last3' ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setViewMode('last3');
                setShowPeriodSelector(false);
              }}
            >
              Last 3 Periods
            </Button>
            <Button
              variant={viewMode === 'last12' ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setViewMode('last12');
                setShowPeriodSelector(false);
              }}
            >
              Last 12 Periods
            </Button>
            <Button
              variant={viewMode === 'single' ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setViewMode('single');
                setShowPeriodSelector(true);
              }}
            >
              Single Period
            </Button>
            <Button
              variant={viewMode === 'compare' ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setViewMode('compare');
                setShowPeriodSelector(true);
              }}
            >
              Compare Periods
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Period Selector for Single/Compare modes */}
        {showPeriodSelector && (
          <div className="p-4 bg-gray-50 rounded-lg border">
            {viewMode === 'single' ? (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Period to View:
                </label>
                <select
                  value={singlePeriod}
                  onChange={(e) => setSinglePeriod(e.target.value)}
                  className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  {availablePeriods.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
            ) : (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium text-gray-700">
                    Select Periods to Compare (max 6):
                  </label>
                  <span className="text-sm text-gray-500">
                    {selectedPeriods.length}/6 selected
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto">
                  {availablePeriods.map(p => (
                    <button
                      key={p.value}
                      onClick={() => handlePeriodToggle(p.value)}
                      className={`px-3 py-1.5 text-sm rounded-lg border transition-colors flex items-center space-x-1 ${
                        selectedPeriods.includes(p.value)
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
                      }`}
                    >
                      {selectedPeriods.includes(p.value) && (
                        <CheckSquare className="h-3 w-3" />
                      )}
                      <span>{p.label}</span>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Tip: Select same months from different years (e.g., Dec 2024 & Dec 2025) to compare year-over-year performance
                </p>
              </div>
            )}
          </div>
        )}

        {/* Summary Stats */}
        {trendData && trendData.length > 0 && (
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-700">
                ₹{formatIndianNumber(totalStats.totalSales)}
              </div>
              <div className="text-sm text-blue-600">Total Sales</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-700">
                {totalStats.periodsCompared}
              </div>
              <div className="text-sm text-green-600">Sales Periods Compared</div>
            </div>
          </div>
        )}

        {/* Chart */}
        {loading ? (
          <div className="h-80 flex items-center justify-center">
            <div className="text-gray-500">Loading trend data...</div>
          </div>
        ) : !trendData || trendData.length === 0 ? (
          <div className="h-80 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <BarChart3 className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>No data available for selected periods</p>
              {viewMode === 'compare' && selectedPeriods.length === 0 && (
                <p className="text-sm">Please select periods to compare</p>
              )}
            </div>
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="day" 
                  type="number"
                  domain={[1, 31]}
                  ticks={[1, 5, 10, 15, 20, 25, 30]}
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Day Number (D1 to DL)', position: 'insideBottom', offset: -15, style: { fontSize: 12 } }}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
                  label={{ value: 'Sales (₹)', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
                />
                <Tooltip 
                  formatter={(value, name) => [`₹${formatTableNumber(value)}`, name]}
                  labelFormatter={(day) => `Day ${day}`}
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
                          <p className="font-semibold mb-2">Day {label}</p>
                          {payload.filter(p => p.value !== null).map((entry, index) => {
                            const periodInfo = trendData.find(t => t.period === entry.dataKey);
                            return (
                              <p key={index} style={{ color: entry.color }} className="text-sm">
                                {periodInfo?.periodLabel || entry.dataKey}: ₹{formatTableNumber(entry.value)}
                              </p>
                            );
                          })}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend 
                  formatter={(value) => {
                    const periodInfo = trendData.find(t => t.period === value);
                    return periodInfo?.periodLabel || value;
                  }}
                />
                
                {trendData.map((period, index) => (
                  <Line
                    key={period.period}
                    dataKey={period.period}
                    name={period.period}
                    stroke={period.color}
                    strokeWidth={2}
                    dot={{ r: 3, fill: period.color }}
                    activeDot={{ r: 5 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>

            {/* Period Summary */}
            <div className="mt-6">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Sales Period Summary</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {trendData.map((period) => (
                  <div 
                    key={period.period}
                    className="p-3 bg-white border rounded-lg shadow-sm"
                  >
                    <div className="flex items-center space-x-2 mb-2">
                      <div 
                        className="w-4 h-4 rounded-full" 
                        style={{ backgroundColor: period.color }}
                      />
                      <span className="font-semibold text-sm">{period.periodLabel}</span>
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      {period.daysTracked} days tracked
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <div className="text-gray-500 text-xs">Total Units</div>
                        <div className="font-semibold">₹{formatTableNumber(period.totalSales)}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 text-xs">Avg/day</div>
                        <div className="font-semibold">₹{formatTableNumber(period.avgDailySales)}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default SalesTrendsChart;
