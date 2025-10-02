import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, X } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DataUpload = ({ onUploadSuccess }) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResults, setUploadResults] = useState([]);

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
            f.id === fileItem.id ? { ...f, status: 'success' } : f
          ));
          results.push({ ...result, filename: fileItem.file.name, success: true });
          toast.success(`Successfully uploaded ${fileItem.file.name}`);
        } else {
          throw new Error(result.detail || 'Upload failed');
        }
      } catch (error) {
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'error', error: error.message } : f
        ));
        results.push({ filename: fileItem.file.name, success: false, error: error.message });
        toast.error(`Failed to upload ${fileItem.file.name}: ${error.message}`);
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
            <span>Upload Sales Data</span>
          </CardTitle>
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
                        <Badge variant="default" className="bg-green-600">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Success
                        </Badge>
                      )}
                      {fileItem.status === 'error' && (
                        <Badge variant="destructive">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          Error
                        </Badge>
                      )}
                      
                      {!uploading && (
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
    </div>
  );
};

export default DataUpload;
