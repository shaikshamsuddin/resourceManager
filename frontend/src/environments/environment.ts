/**
 * Environment configuration for development
 */
export const environment = {
  production: false,
  api: {
    host: '134.33.229.191',
    port: 80,  // Backend is running on port 5005 (avoiding macOS AirPlay conflict)
    protocol: 'http'
  }
}; 