import React from 'react';
import { JobStatus } from '../types';

interface JobStatusCardProps {
  jobStatus: JobStatus;
  originalImageUrl?: string;
}

const JobStatusCard: React.FC<JobStatusCardProps> = ({ jobStatus, originalImageUrl }) => {
  const getStatusBadge = () => {
    switch (jobStatus.status) {
      case 'processing':
        return (
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-orange-100 text-orange-600 rounded-full text-sm font-medium">
            <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
            Processing...
          </div>
        );
      case 'completed':
        return (
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-green-100 text-green-600 rounded-full text-sm font-medium">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            Completed
          </div>
        );
      case 'failed':
        return (
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-red-100 text-red-600 rounded-full text-sm font-medium">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            Failed
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="my-6 p-6 bg-gray-50/80 backdrop-blur-sm rounded-xl">
      <div className="mb-4">
        {getStatusBadge()}
      </div>
      
      {jobStatus.status === 'processing' && (
        <div className="w-full bg-gray-200 rounded-full h-1 mb-4">
          <div className="bg-gradient-to-r from-blue-500 to-purple-600 h-1 rounded-full w-3/5 animate-pulse"></div>
        </div>
      )}

      {jobStatus.status === 'completed' && jobStatus.downloadUrl && originalImageUrl && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Original Image */}
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-700 text-center">Original</h3>
              <div className="rounded-xl overflow-hidden shadow-lg bg-white">
                <img 
                  src={originalImageUrl} 
                  alt="Original" 
                  className="w-full h-auto"
                />
              </div>
            </div>
            
            {/* Upscaled Image */}
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-700 text-center">AI Enhanced (4x)</h3>
              <div className="rounded-xl overflow-hidden shadow-lg bg-white">
                <img 
                  src={jobStatus.downloadUrl} 
                  alt="AI Enhanced" 
                  className="w-full h-auto"
                />
              </div>
            </div>
          </div>
          
          <button 
            className="apple-button w-full"
            onClick={() => window.open(jobStatus.downloadUrl, '_blank')}
          >
            Download Enhanced Image
          </button>
        </div>
      )}

      {jobStatus.error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          Error: {jobStatus.error}
        </div>
      )}
    </div>
  );
};

export default JobStatusCard;
