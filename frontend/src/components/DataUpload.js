import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, X, Trash2, Undo2 } from "lucide-react";
import { toast } from "sonner";
import { ErrorDialog } from "./ui/error-dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DataUpload = ({ onUploadSuccess }) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResults, setUploadResults] = useState([]);
  const [errorDialog, setErrorDialog] = useState({ open: false, title: "", message: "", details: "" });
  const [showResetDialog, setShowResetDialog] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [undoDialog, setUndoDialog] = useState({ open: false, upload: null });
  const [undoing, setUndoing] = useState(false);

  const onDrop = useCallback((acceptedFiles) => {
    const excelFiles = acceptedFiles.filter(file => {
      const extension = file.name.toLowerCase().split('.').pop();
      return ['xlsx', 'xls'].includes(extension);
    });

    if (excelFiles.length !== acceptedFiles.length) {
      toast.error("Only Excel files (.xlsx, .xls) are supported");
    }

    const newFiles = excelFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending',
      progress: 0
    }));

    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: true
  });

  const removeFile = (fileId) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const uploadFiles = async () => {
    if (files.length === 0) {
      toast.error("Please select files to upload");
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    const results = [];

    for (let i = 0; i < files.length; i++) {
      const fileItem = files[i];
      
      try {
        // Update file status
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'uploading' } : f
        ));

        const formData = new FormData();
        formData.append('file', fileItem.file);

        const response = await fetch(`${API}/upload-sales-data`, {
          method: 'POST',
          body: formData,
        });

        const result = await response.json();

        if (response.ok) {
          setFiles(prev => prev.map(f => 
            f.id === fileItem.id ? { ...f, status: 'success', upload_id: result.upload_id } : f
          ));
          results.push({ ...result, filename: fileItem.file.name, success: true, upload_id: result.upload_id });
          toast.success(`Successfully uploaded ${fileItem.file.name}${result.period_covered ? ` (${result.period_covered})` : ''}`);
        } else {
          throw new Error(result.detail || 'Upload failed');
        }
      } catch (error) {
        const errorMessage = error.message;
        
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'error', error: errorMessage } : f
        ));
        results.push({ filename: fileItem.file.name, success: false, error: errorMessage });
        
        // Show error in modal dialog instead of toast
        setErrorDialog({
          open: true,
          title: `Failed to upload ${fileItem.file.name}`,
          message: errorMessage,
          details: errorMessage.includes("No valid records found") 
            ? "The file was read successfully, but no valid data rows were found. This may happen if:\n\n• The data rows don't match the expected format\n• Item names are missing or invalid\n• Product codes (pluno) are not in the correct format\n• All rows were filtered out due to data quality issues\n\nPlease check the file format requirements below and try again."
            : errorMessage.includes("Excel file format") 
            ? "The file could not be read as an Excel file. Please ensure:\n\n• The file is a valid .xlsx or .xls format\n• The file is not corrupted\n• The file is not password-protected\n• You have the latest version of Excel or LibreOffice"
            : "An unexpected error occurred while processing the file. Please check the error message above for more details."
        });
      }

      // Update progress
      setUploadProgress(((i + 1) / files.length) * 100);
    }

    setUploadResults(results);
    setUploading(false);
    
    // Call success callback to refresh dashboard
    if (results.some(r => r.success)) {
      onUploadSuccess();
    }
  };

  const clearAll = () => {
    setFiles([]);
    setUploadResults([]);
    setUploadProgress(0);
  };

  const handleUndoUpload = async () => {
    if (!undoDialog.upload) return;
    
    setUndoing(true);
    try {
      const response = await fetch(`${API}/undo-upload/${undoDialog.upload.upload_id}`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (response.ok) {
        toast.success(`Successfully undone: ${undoDialog.upload.filename}. Deleted ${result.deleted_count} records.`);
        
        // Remove from files list
        setFiles(prev => prev.filter(f => f.upload_id !== undoDialog.upload.upload_id));
        
        // Remove from results
        setUploadResults(prev => prev.filter(r => r.upload_id !== undoDialog.upload.upload_id));
        
        setUndoDialog({ open: false, upload: null });
        
        if (onUploadSuccess) {
          onUploadSuccess(); // Refresh dashboard
        }
      } else {
        throw new Error(result.detail || 'Undo failed');
      }
    } catch (error) {
      console.error("Error undoing upload:", error);
      toast.error(`Failed to undo upload: ${error.message}`);
    } finally {
      setUndoing(false);
    }
  };

  const handleResetDatabase = async () => {
    setResetting(true);
    try {
      const response = await fetch(`${API}/reset-all-data`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (response.ok) {
        toast.success(`Database reset successful! Deleted ${result.sales_records_deleted} sales records and ${result.upload_history_deleted} upload history entries.`);
        setShowResetDialog(false);
        if (onUploadSuccess) {
          onUploadSuccess(); // Refresh dashboard
        }
      } else {
        throw new Error(result.detail || 'Reset failed');
      }
    } catch (error) {
      console.error("Error resetting database:", error);
      toast.error(`Failed to reset database: ${error.message}`);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>Data Upload Instructions</CardTitle>
          <CardDescription>
            Upload your Excel sales data files to analyze performance and generate insights
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-900 mb-2">Required Excel Format:</h4>
            <div className="text-sm text-blue-800 space-y-1">
              <p>• <strong>Columns:</strong> S.No, GP_Index, pluno, Item_Name, W_Rate, R_Rate, Qty, Refund_Qty, Net_Qty, R_Amt, W_Amt, Profit, O_B, Closing_Stock, Net_Tax</p>
              <p>• <strong>File Types:</strong> .xlsx or .xls files only</p>
              <p>• <strong>Data Period:</strong> Include year/month in filename (e.g., "Yr 2024 C.xlsx")</p>
              <p>• <strong>Product Groups:</strong> Items should have group codes (I/, II/, III/, IV/, VI/)</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* File Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Upload className="h-5 w-5" />
            <span>Upload Historical Data</span>
          </CardTitle>
          <CardDescription>
            Upload historical sales data for months or years. For today's data, use the "Upload Today's Data" button on the dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-blue-400 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            data-testid="file-dropzone"
          >
            <input {...getInputProps()} data-testid="file-input" />
            <FileSpreadsheet className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            {isDragActive ? (
              <div>
                <p className="text-lg font-medium text-blue-600">Drop files here...</p>
                <p className="text-gray-600">Release to upload your Excel files</p>
              </div>
            ) : (
              <div>
                <p className="text-lg font-medium text-gray-900 mb-2">Drop Excel files here, or click to select</p>
                <p className="text-gray-600">Support for .xlsx and .xls files</p>
                <p className="text-sm text-gray-500 mt-2">You can upload multiple files at once</p>
              </div>
            )}
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="mt-6 space-y-3">
              <div className="flex justify-between items-center">
                <h4 className="font-medium">Selected Files ({files.length})</h4>
                <Button variant="outline" size="sm" onClick={clearAll} disabled={uploading}>
                  Clear All
                </Button>
              </div>
              
              <div className="space-y-2">
                {files.map((fileItem) => (
                  <div key={fileItem.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border">
                    <div className="flex items-center space-x-3">
                      <FileSpreadsheet className="h-5 w-5 text-green-600" />
                      <div>
                        <p className="font-medium text-sm">{fileItem.file.name}</p>
                        <p className="text-xs text-gray-500">
                          {(fileItem.file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {fileItem.status === 'pending' && (
                        <Badge variant="secondary">Pending</Badge>
                      )}
                      {fileItem.status === 'uploading' && (
                        <Badge variant="outline">Uploading...</Badge>
                      )}
                      {fileItem.status === 'success' && (
                        <>
                          <Badge variant="default" className="bg-green-600">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Success
                          </Badge>
                          {fileItem.upload_id && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setUndoDialog({ open: true, upload: { upload_id: fileItem.upload_id, filename: fileItem.file.name } })}
                              className="text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                            >
                              <Undo2 className="h-3 w-3 mr-1" />
                              Undo
                            </Button>
                          )}
                        </>
                      )}
                      {fileItem.status === 'error' && (
                        <Badge variant="destructive">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          Error
                        </Badge>
                      )}
                      
                      {!uploading && fileItem.status !== 'success' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFile(fileItem.id)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {uploading && (
            <div className="mt-6 space-y-2">
              <div className="flex justify-between text-sm">
                <span>Upload Progress</span>
                <span>{Math.round(uploadProgress)}%</span>
              </div>
              <Progress value={uploadProgress} className="w-full" />
            </div>
          )}

          {/* Action Buttons */}
          {files.length > 0 && (
            <div className="mt-6 flex space-x-3">
              <Button
                onClick={uploadFiles}
                disabled={uploading || files.every(f => f.status === 'success')}
                className="flex-1"
                data-testid="upload-button"
              >
                {uploading ? 'Uploading...' : 'Upload Files'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Results */}
      {uploadResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {uploadResults.map((result, index) => (
                <div
                  key={index}
                  className={`p-4 rounded-lg border ${
                    result.success
                      ? 'bg-green-50 border-green-200'
                      : 'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{result.filename}</p>
                      {result.success ? (
                        <div className="text-green-700 text-sm mt-1">
                          <p>✅ Successfully processed {result.records_count} records</p>
                        </div>
                      ) : (
                        <p className="text-red-700 text-sm mt-1">❌ {result.error}</p>
                      )}
                    </div>
                    {result.success ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-red-600" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Database Management */}
      <Card className="border-red-200 bg-red-50">
        <CardHeader>
          <CardTitle className="text-red-900 flex items-center">
            <Trash2 className="h-5 w-5 mr-2" />
            Database Management
          </CardTitle>
          <CardDescription className="text-red-700">
            Danger Zone: Clear all uploaded data from the database
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-white rounded-lg border border-red-200">
            <p className="text-sm text-gray-700 mb-4">
              <strong>Warning:</strong> This action will permanently delete all sales records and upload history from the database. This cannot be undone.
            </p>
            <Button
              variant="destructive"
              onClick={() => setShowResetDialog(true)}
              className="w-full"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Reset All Sales Data
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* Error Dialog */}
      <ErrorDialog
        open={errorDialog.open}
        onOpenChange={(open) => setErrorDialog({ ...errorDialog, open })}
        title={errorDialog.title}
        message={errorDialog.message}
        details={errorDialog.details}
      />
      
      {/* Reset Confirmation Dialog */}
      <AlertDialog open={showResetDialog} onOpenChange={setShowResetDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-red-900">Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-700">
              This will permanently delete:
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>All sales records from the database</li>
                <li>All upload history logs</li>
                <li>All analytics and forecast data</li>
              </ul>
              <p className="mt-3 font-semibold text-red-700">
                This action cannot be undone. You will need to re-upload all your data.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleResetDatabase}
              disabled={resetting}
              className="bg-red-600 hover:bg-red-700"
            >
              {resetting ? "Resetting..." : "Yes, Reset Database"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      
      {/* Undo Upload Confirmation Dialog */}
      <AlertDialog open={undoDialog.open} onOpenChange={(open) => setUndoDialog({ ...undoDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-orange-900">Undo This Upload?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-700">
              {undoDialog.upload && (
                <>
                  <p className="mb-3">
                    This will delete all records uploaded from:
                  </p>
                  <div className="p-3 bg-gray-50 rounded border">
                    <strong className="text-sm">{undoDialog.upload.filename}</strong>
                  </div>
                  <p className="mt-3 font-semibold text-orange-700">
                    This cannot be undone. You will need to re-upload the file if needed.
                  </p>
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleUndoUpload}
              disabled={undoing}
              className="bg-orange-600 hover:bg-orange-700"
            >
              {undoing ? "Undoing..." : "Yes, Undo Upload"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default DataUpload;
