import { headers } from 'next/headers';

export default function AccountSettingsPage() {
  const headersList = headers();
  const sessionId = headersList.get('x-session-id');
  
  return (
    <div className="container">
      <h1>Account Settings</h1>
      <p>Session ID: {sessionId}</p>
      <p>This page contains sensitive information and should not be cached.</p>
      
      <div className="settings-form">
        <h2>Profile Settings</h2>
        <div className="form-group">
          <label htmlFor="name">Name</label>
          <input type="text" id="name" className="input" defaultValue="John Doe" />
        </div>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input type="email" id="email" className="input" defaultValue="john@example.com" />
        </div>
        <button className="save-button">Save Changes</button>
      </div>
    </div>
  );
}

// This page should have no-cache headers
export async function generateMetadata() {
  return {
    title: 'Account Settings',
    description: 'Manage your account settings and preferences',
  };
}