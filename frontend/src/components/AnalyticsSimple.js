import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Skeleton } from "./ui/skeleton";
import { TrendingUp } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AnalyticsSimple = () => {
  const [fastestItems, setFastestItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('Fetching analytics data...');
      
      const response = await fetch(`${API}/fastest-selling-items?limit=10`);
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Data received:', data.length, 'items');
      
      setFastestItems(data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching analytics data:", error);
      setError(error.message);
      setLoading(false);
      toast.error(`Failed to load analytics data: ${error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800">Error Loading Analytics</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700">Error: {error}</p>
            <Button onClick={fetchAnalyticsData} className="mt-4">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5" />
            <span>Simple Analytics Test</span>
          </CardTitle>
          <CardDescription>
            Testing basic analytics functionality
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-green-600 font-medium">
              ✅ Analytics data loaded successfully! {fastestItems.length} items found.
            </p>
            
            <div className="space-y-2">
              <h4 className="font-semibold">Top 5 Items:</h4>
              {fastestItems.slice(0, 5).map((item, index) => (
                <div key={index} className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-medium">#{index + 1}. {item.item_code} - {item.item_name}</p>
                  <p className="text-sm text-gray-600">
                    Sold: {item.total_sold} units | Revenue: ₹{(item.total_revenue || 0).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
            
            <Button onClick={fetchAnalyticsData} className="mt-4">
              Refresh Data
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AnalyticsSimple;