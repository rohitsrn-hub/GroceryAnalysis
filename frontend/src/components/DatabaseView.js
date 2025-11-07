import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Badge } from "./ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Download, RefreshCw, Search, Database, Filter, Calendar, Package } from "lucide-react";
import { toast } from "sonner";
import { formatIndianNumber } from "../utils/numberUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DatabaseView = () => {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [totalRecords, setTotalRecords] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(50);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [groupFilter, setGroupFilter] = useState("all");
  const [periodFilter, setPeriodFilter] = useState("");

  useEffect(() => {
    fetchRecords();
  }, [page, groupFilter, periodFilter]);

  // Reset page when filters change
  useEffect(() => {
    if (page !== 0) {
      setPage(0);
    }
  }, [groupFilter, periodFilter, searchTerm]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        skip: (page * limit).toString()
      });

      if (searchTerm) params.append("search", searchTerm);
      if (groupFilter !== "all") params.append("group_filter", groupFilter);
      if (periodFilter && periodFilter !== "all-periods") params.append("period_filter", periodFilter);

      const response = await fetch(`${API}/database-view?${params}`);
      if (!response.ok) throw new Error("Failed to fetch records");

      const data = await response.json();
      setRecords(data.records || []);
      setTotalRecords(data.total || 0);
      setSummary(data.summary || null);
    } catch (error) {
      console.error("Error fetching database records:", error);
      toast.error("Failed to load database records");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(0);
    fetchRecords();
  };

  const exportToCSV = () => {
    if (records.length === 0) {
      toast.error("No records to export");
      return;
    }

    const headers = [
      "Item Code",
      "Item Name",
      "Product Group",
      "Quantity Sold",
      "Net Quantity",
      "Wholesale Rate",
      "Retail Rate",
      "Wholesale Amount",
      "Retail Amount",
      "Profit",
      "Closing Stock",
      "Opening Balance",
      "Net Tax",
      "Data Period",
      "Upload Date"
    ];

    const csvRows = [headers.join(",")];

    records.forEach(record => {
      const row = [
        `"${record.pluno || ''}"`,
        `"${record.item_name || ''}"`,
        `"${record.product_group || ''}"`,
        record.qty || 0,
        record.net_qty || 0,
        (record.w_rate || 0).toFixed(2),
        (record.r_rate || 0).toFixed(2),
        (record.w_amt || 0).toFixed(2),
        (record.r_amt || 0).toFixed(2),
        (record.profit || 0).toFixed(2),
        record.closing_stock || 0,
        record.o_b || 0,
        (record.net_tax || 0).toFixed(2),
        `"${record.data_period || ''}"`,
        `"${new Date(record.upload_date).toLocaleString()}"`
      ];
      csvRows.push(row.join(","));
    });

    const csvContent = csvRows.join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);

    link.setAttribute("href", url);
    link.setAttribute("download", `database-export-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast.success("Database records exported successfully");
  };

  const totalPages = Math.ceil(totalRecords / limit);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center">
            <Database className="h-6 w-6 mr-2 text-cyan-600" />
            Database View
          </CardTitle>
          <CardDescription>
            Browse and analyze all sales records in the database
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Summary Stats */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="p-4 bg-cyan-50 rounded-lg border border-cyan-200">
                <div className="text-sm text-cyan-600 font-medium">Total Records</div>
                <div className="text-2xl font-bold text-cyan-900">
                  {summary.total_records.toLocaleString()}
                </div>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-sm text-blue-600 font-medium">Available Periods</div>
                <div className="text-2xl font-bold text-blue-900">
                  {summary.available_periods?.length || 0}
                </div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div className="text-sm text-purple-600 font-medium">Product Groups</div>
                <div className="text-2xl font-bold text-purple-900">
                  {summary.available_groups?.length || 0}
                </div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="text-sm text-green-600 font-medium">Date Range</div>
                <div className="text-sm font-medium text-green-900">
                  {summary.date_range?.earliest && summary.date_range?.latest ? (
                    <>
                      {new Date(summary.date_range.earliest).toLocaleDateString()} - {new Date(summary.date_range.latest).toLocaleDateString()}
                    </>
                  ) : "N/A"}
                </div>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap gap-4 mb-6">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block flex items-center">
                <Search className="h-4 w-4 mr-1" />
                Search Item Name
              </label>
              <div className="flex gap-2">
                <Input
                  placeholder="Search by item name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                />
                <Button onClick={handleSearch} size="icon">
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="w-48">
              <label className="text-sm font-medium mb-2 block flex items-center">
                <Package className="h-4 w-4 mr-1" />
                Product Group
              </label>
              <Select value={groupFilter} onValueChange={setGroupFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Groups</SelectItem>
                  {summary?.available_groups?.filter(group => group && group.trim() !== '').map(group => (
                    <SelectItem key={group} value={group}>{group}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="w-48">
              <label className="text-sm font-medium mb-2 block flex items-center">
                <Calendar className="h-4 w-4 mr-1" />
                Period Filter
              </label>
              <Select value={periodFilter} onValueChange={setPeriodFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Periods" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all-periods">All Periods</SelectItem>
                  {summary?.available_periods?.filter(period => period && period.trim() !== '').map(period => (
                    <SelectItem key={period} value={period}>{period}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2 items-end">
              <Button onClick={fetchRecords} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button onClick={exportToCSV} variant="outline" disabled={records.length === 0}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="text-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-cyan-600" />
              <p className="text-gray-600">Loading database records...</p>
            </div>
          ) : records.length === 0 ? (
            <div className="text-center py-12">
              <Database className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600">No records found</p>
              <p className="text-sm text-gray-500 mt-2">Try adjusting your filters or upload some data</p>
            </div>
          ) : (
            <>
              <div className="border rounded-lg overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item Code</TableHead>
                      <TableHead>Item Name</TableHead>
                      <TableHead>Group</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">W. Rate</TableHead>
                      <TableHead className="text-right">R. Rate</TableHead>
                      <TableHead className="text-right">W. Amt</TableHead>
                      <TableHead className="text-right">R. Amt</TableHead>
                      <TableHead className="text-right">Profit</TableHead>
                      <TableHead className="text-right">Stock</TableHead>
                      <TableHead>Period</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {records.map((record, index) => (
                      <TableRow key={record.id || index}>
                        <TableCell className="font-mono text-xs">
                          {record.pluno || "N/A"}
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <div className="truncate" title={record.item_name}>
                            {record.item_name?.substring(0, 40)}
                            {record.item_name?.length > 40 ? "..." : ""}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {record.product_group || "Unknown"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {record.net_qty || 0}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          ₹{(record.w_rate || 0).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          ₹{(record.r_rate || 0).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          ₹{(record.w_amt || 0).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          ₹{(record.r_amt || 0).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          <span className={record.profit > 0 ? "text-green-600" : "text-red-600"}>
                            ₹{(record.profit || 0).toFixed(2)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {record.closing_stock || 0}
                        </TableCell>
                        <TableCell>
                          <Badge className="text-xs">{record.data_period || "N/A"}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-gray-600">
                  Showing {page * limit + 1} to {Math.min((page + 1) * limit, totalRecords)} of {totalRecords.toLocaleString()} records
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
                  <div className="flex items-center px-4 py-2 bg-gray-100 rounded">
                    Page {page + 1} of {totalPages}
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page >= totalPages - 1}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DatabaseView;
