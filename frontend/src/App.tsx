import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { User, JobStatus, GoogleCredentialResponse, UploadResponse, DownloadResponse } from './types';
import GoogleSignInButton from './components/GoogleSignInButton';
import UserInfo from './components/UserInfo';
import UploadArea from './components/UploadArea';
import JobStatusCard from './components/JobStatusCard';

const API_BASE_URL = 'http://localhost:8080';

declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          cancel: () => void;
          initialize: (config: { client_id: string; callback: (response: GoogleCredentialResponse) => void; use_fedcm_for_prompt?: boolean }) => void;
          prompt: (notificationCallback?: (notification: { isNotDisplayed: () => boolean; isSkippedMoment: () => boolean }) => void) => void;
          renderButton: (element: HTMLElement | null, options: { 
            theme: string; 
            size: string; 
            width?: string;
            type?: string;
            shape?: string;
          }) => void;
        };
      };
    };
  }
}

const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [dragOver, setDragOver] = useState<boolean>(false);
  const [showFallback, setShowFallback] = useState<boolean>(false);
  const [buttonLoaded, setButtonLoaded] = useState<boolean>(false);
  const [isInitialized, setIsInitialized] = useState<boolean>(false);

  // Load cached user on component mount
  useEffect(() => {
    const cachedUser = localStorage.getItem('ai-upscaler-user');
    if (cachedUser) {
      try {
        const userData = JSON.parse(cachedUser);
        setUser(userData);
        console.log('Restored user from cache:', userData);
      } catch (error) {
        console.error('Failed to parse cached user:', error);
        localStorage.removeItem('ai-upscaler-user');
      }
    }
    setIsInitialized(true);
  }, []);

  const renderGoogleFallbackButton = () => {
    setTimeout(() => {
      const fallbackElement = document.getElementById('google-signin-fallback');
      const elementWidth = fallbackElement?.offsetWidth || 320;
      window.google?.accounts.id.renderButton(
        fallbackElement,
        { 
          theme: 'outline', 
          size: 'large',
          width: `${elementWidth - 12}px`
        }
      );
      
      // Wait a bit more for the button to fully render
      setTimeout(() => {
        setButtonLoaded(true);
      }, 500);
    }, 100);
  };

  useEffect(() => {
    console.log('Google Client ID:', process.env.REACT_APP_GOOGLE_CLIENT_ID);
    
    // Only initialize Google Sign-In if user is not already signed in AND we've checked cache
    if (!user && isInitialized && window.google) {
      window.google.accounts.id.cancel();

      setTimeout(() => {
        console.log('Initializing Google Sign-In...');
        window.google.accounts.id.initialize({
          client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID || '',
          callback: handleGoogleSignIn,
        });
        
        // Trigger prompt immediately after initialization
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            console.log('Google Sign-In prompt not displayed or skipped', notification);
            setShowFallback(true);
            renderGoogleFallbackButton();
          }
        });
      }, 100);
    }
  }, [user, isInitialized]);

  const handleGoogleSignIn = (response: GoogleCredentialResponse): void => {
    try {
      // Decode JWT token (in production, verify on backend)
      console.log('Google Sign-In Response:', response);
      const payload = JSON.parse(atob(response.credential.split('.')[1]));
      const userData = {
        name: payload.name,
        email: payload.email,
        picture: payload.picture
      };
      
      setUser(userData);
      // Cache user data in localStorage
      localStorage.setItem('ai-upscaler-user', JSON.stringify(userData));
      console.log('User data cached:', userData);
    } catch (error) {
      console.error('Failed to decode Google credential:', error);
    }
  };

  const signOut = (): void => {
    setUser(null);
    setSelectedFile(null);
    setJobStatus(null);
    setOriginalImageUrl(null);
    // Clear cached user data
    localStorage.removeItem('ai-upscaler-user');
    console.log('User signed out and cache cleared');
    // Cancel Google Sign-In session
    if (window.google) {
      window.google.accounts.id.cancel();
    }
  };

  const handleFileSelect = (file: File): void => {
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setJobStatus(null);
      
      // Create preview URL for original image
      const reader = new FileReader();
      reader.onload = (e) => {
        setOriginalImageUrl(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const clearSelectedFile = (): void => {
    setSelectedFile(null);
    setJobStatus(null);
    setOriginalImageUrl(null);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    setDragOver(false);
  };

  const uploadImage = async (): Promise<void> => {
    if (!selectedFile) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post<UploadResponse>(`${API_BASE_URL}/upscale`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setJobStatus({
        ...response.data,
        status: 'processing'
      });

      // Poll for completion
      pollJobStatus(response.data.job_id);
    } catch (error) {
      console.error('Upload failed:', error);
      setJobStatus({
        job_id: '',
        status: 'failed',
        error: error instanceof Error ? error.message : 'Upload failed'
      });
    } finally {
      setUploading(false);
    }
  };

  const pollJobStatus = async (jobId: string): Promise<void> => {
    const maxAttempts = 30;
    let attempts = 0;

    const poll = async (): Promise<void> => {
      try {
        const response = await axios.get<DownloadResponse>(`${API_BASE_URL}/download/${jobId}`);
        setJobStatus(prev => prev ? {
          ...prev,
          status: 'completed',
          downloadUrl: response.data.download_url
        } : null);
      } catch (error) {
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          setJobStatus(prev => prev ? {
            ...prev,
            status: 'failed',
            error: 'Processing timeout'
          } : null);
        }
      }
    };

    setTimeout(poll, 2000);
  };
  console.log('Button Loaded:', buttonLoaded);

  const handleTestImage = async (): Promise<void> => {
    try {
      const response = await fetch('https://upload.wikimedia.org/wikipedia/en/thumb/a/af/Fallout.jpg/250px-Fallout.jpg');
      const blob = await response.blob();
      const file = new File([blob], 'Fallout.jpg', { type: 'image/jpeg' });
      handleFileSelect(file);
    } catch (error) {
      console.error('Failed to load test image:', error);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-400 via-purple-500 to-purple-700 flex items-center justify-center p-5">
        <div className="glass-card rounded-3xl p-10 max-w-md w-full text-center">
          <div className="text-4xl font-bold mb-3 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            AI Upscaler
          </div>
          <div className="text-lg text-gray-600 mb-10 font-medium">
            Enhance your images with artificial intelligence
          </div>
          
          <div className="w-full h-12 flex items-center justify-center relative">
            <div className={`text-gray-500 transition-opacity duration-300 ${buttonLoaded ? 'opacity-0' : 'opacity-100'}`}>
              Loading sign-in...
            </div>
            {showFallback && (
              <div 
                id="google-signin-fallback" 
                className={`w-full absolute inset-0 transition-opacity duration-300 ${buttonLoaded ? 'opacity-100' : 'opacity-0 invisible'}`}
              ></div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-400 via-purple-500 to-purple-700 flex items-center justify-center p-5">
      <div className="glass-card rounded-3xl p-10 max-w-4xl w-full">
        <UserInfo user={user} onSignOut={signOut} />

        <div className="text-center mb-8">
          <div className="text-4xl font-bold mb-3 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            AI Upscaler
          </div>
          <div className="text-lg text-gray-600 font-medium">
            Upload an image to enhance with AI
          </div>
        </div>

        <UploadArea
          selectedFile={selectedFile}
          dragOver={dragOver}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => document.getElementById('file-input')?.click()}
          onClearFile={clearSelectedFile}
        />

        <input
          id="file-input"
          type="file"
          className="hidden"
          accept="image/*"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileSelect(file);
          }}
        />

        {!selectedFile && (
          <div className="text-center mb-4">
            <button 
              className="apple-button-secondary text-sm"
              onClick={handleTestImage}
            >
              Use Test Image
            </button>
          </div>
        )}

        {selectedFile && (
          <button 
            className={`apple-button w-full flex items-center justify-center gap-2 ${uploading ? 'opacity-60 cursor-not-allowed' : ''}`}
            onClick={uploadImage}
            disabled={uploading}
          >
            {uploading && (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            )}
            {uploading ? 'Uploading...' : 'Upscale Image'}
          </button>
        )}

        {jobStatus && <JobStatusCard jobStatus={jobStatus} originalImageUrl={originalImageUrl ?? undefined} />}
      </div>
    </div>
  );
};

export default App;
