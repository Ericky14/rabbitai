import React from 'react';

interface UploadAreaProps {
  selectedFile: File | null;
  dragOver: boolean;
  onDrop: (e: React.DragEvent<HTMLDivElement>) => void;
  onDragOver: (e: React.DragEvent<HTMLDivElement>) => void;
  onDragLeave: (e: React.DragEvent<HTMLDivElement>) => void;
  onClick: () => void;
  onClearFile: () => void;
}

const UploadArea: React.FC<UploadAreaProps> = ({
  selectedFile,
  dragOver,
  onDrop,
  onDragOver,
  onDragLeave,
  onClick,
  onClearFile
}) => {
  const [imagePreview, setImagePreview] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(selectedFile);
    } else {
      setImagePreview(null);
    }
  }, [selectedFile]);

  if (selectedFile && imagePreview) {
    return (
      <div className="my-6">
        <div className="relative rounded-2xl overflow-hidden shadow-lg bg-gray-50">
          <img 
            src={imagePreview} 
            alt="Selected" 
            className="w-full h-auto max-h-96 object-contain"
          />
          <button
            onClick={onClearFile}
            className="absolute top-3 right-3 w-8 h-8 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center transition-colors duration-200 shadow-lg"
          >
            ✕
          </button>
        </div>
        <div className="text-center mt-3">
          <p className="text-sm text-gray-600 font-medium">{selectedFile.name}</p>
          <button
            onClick={onClick}
            className="text-blue-500 hover:text-blue-600 text-sm font-medium mt-1 transition-colors duration-200"
          >
            Choose different image
          </button>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`
        border-2 border-dashed rounded-2xl p-12 my-6 cursor-pointer transition-all duration-300
        ${dragOver 
          ? 'border-blue-400 bg-blue-50/50 scale-105' 
          : 'border-gray-300 bg-gray-50/30 hover:border-blue-300 hover:bg-blue-50/30'
        }
      `}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={onClick}
    >
      <div className="text-center">
        <div className="text-5xl mb-4 text-gray-400">📸</div>
        <div className="text-lg font-medium text-gray-700 mb-2">
          Drop an image here or click to browse
        </div>
        <div className="text-sm text-gray-500">
          Supports JPG, PNG, WebP up to 10MB
        </div>
      </div>
    </div>
  );
};

export default UploadArea;
