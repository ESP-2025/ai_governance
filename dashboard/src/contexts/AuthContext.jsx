/**
 * Authentication Context using Auth0
 * Handles SSO login/logout
 */
import { createContext, useContext, useEffect, useState } from 'react';
import { Auth0Provider, useAuth0 } from '@auth0/auth0-react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const domain = import.meta.env.VITE_AUTH0_DOMAIN;
  const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID;
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE;

  if (!domain || !clientId) {
    console.error("Auth0 configuration missing. Check .env file.");
    return <div>Configuration Error: Missing Auth0 credentials</div>;
  }

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: audience,
      }}
    >
      <AuthContent>{children}</AuthContent>
    </Auth0Provider>
  );
}

// Helper component to expose Auth0 hook values to the context
function AuthContent({ children }) {
  const auth0 = useAuth0();

  // Normalize user object if needed, or pass auth0 directly
  const value = {
    ...auth0,
    // Provide explicit isAuthenticated check if needed, though auth0.isAuthenticated is standard
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}