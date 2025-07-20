import React from 'react';
import { User } from '../types';

interface UserInfoProps {
  user: User;
  onSignOut: () => void;
}

const UserInfo: React.FC<UserInfoProps> = ({ user, onSignOut }) => {
  return (
    <div className="flex items-center justify-between mb-8 p-4 bg-gray-50/50 backdrop-blur-sm rounded-xl border border-white/20 shadow-lg">
      <div className="flex items-center gap-3">
        <img 
          src={user.picture} 
          alt="Profile" 
          className="w-10 h-10 rounded-full ring-2 ring-white shadow-sm"
        />
        <div>
          <div className="font-semibold text-gray-900">{user.name}</div>
          <div className="text-sm text-gray-500">{user.email}</div>
        </div>
      </div>
      <button 
        className="apple-button-secondary text-sm"
        onClick={onSignOut}
      >
        Sign Out
      </button>
    </div>
  );
};

export default UserInfo;
