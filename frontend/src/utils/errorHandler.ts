export function handleApiError(error: any): string {
  if (error.response) {
    // Server responded with error status
    if (error.response.status === 401) {
      // Unauthorized - redirect to login
      localStorage.removeItem('token');
      window.location.href = '/login';
      return 'Session expired. Please login again.';
    }
    if (error.response.status === 403) {
      return 'You do not have permission to perform this action.';
    }
    if (error.response.status === 404) {
      return 'Resource not found.';
    }
    if (error.response.status === 429) {
      return 'Too many requests. Please try again later.';
    }
    if (error.response.status >= 500) {
      return 'Server error. Please try again later.';
    }
    return error.response.data?.message || error.response.data?.error || 'An error occurred.';
  }
  
  if (error.request) {
    // Request made but no response
    return 'Network error. Please check your connection.';
  }
  
  // Other errors
  return error.message || 'An unexpected error occurred.';
}

export function isNetworkError(error: any): boolean {
  return !error.response && error.request;
}

export function isAuthError(error: any): boolean {
  return error.response?.status === 401 || error.response?.status === 403;
}

