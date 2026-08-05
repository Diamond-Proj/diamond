export interface TokenData {
  access_token: string;
  refresh_token: string | null;
  expires_at_seconds: number;
  resource_server: string;
  token_type: string;
  scope: string;
}

export interface IdTokenIdentity {
  sub: string;
  organization?: string;
  name?: string;
  username?: string;
  identity_provider?: string;
  identity_provider_display_name?: string;
  email?: string;
  last_authentication?: number;
}

export interface IdTokenClaims {
  sub: string;
  organization?: string;
  name?: string;
  preferred_username?: string;
  identity_provider?: string;
  identity_provider_display_name?: string;
  amr?: string[] | null;
  acr?: string;
  email?: string;
  last_authentication?: number;
  identity_set?: IdTokenIdentity[];
  iss?: string;
  aud?: string | string[];
  exp?: number;
  iat?: number;
  at_hash?: string;
}

export interface TokenStore {
  by_resource_server: Record<string, TokenData>;
  id_token?: string;
  id_token_claims?: IdTokenClaims;
}

export interface UserInfo {
  id: string;
  name?: string;
  email?: string;
  username?: string;
  organization?: string;
}

export interface AuthSession {
  isAuthenticated: boolean;
  userInfo: UserInfo | null;
  needsRefresh: boolean;
  nextRefreshAtSeconds: number | null;
}

export interface GlobusTokenResponse {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
  resource_server?: string;
  token_type?: string;
  scope?: string;
  id_token?: string;
  other_tokens?: Array<{
    access_token: string;
    refresh_token?: string;
    expires_in?: number;
    resource_server?: string;
    token_type?: string;
    scope?: string;
  }>;
}

export const GLOBUS_COMPUTE_SCOPE =
  'https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all';
export const REFRESH_BUFFER_SECONDS = 300; // 5 minutes before expiry
export const TOKEN_COOKIE_MAX_AGE = 7 * 24 * 60 * 60; // 7 days
