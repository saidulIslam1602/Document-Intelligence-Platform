/**
 * Role-based access control utilities
 */

export type UserRole = 'admin' | 'user' | 'developer';

export interface Permission {
  viewAnalytics: boolean;
  viewAuditLogs: boolean;
  viewApiKeys: boolean;
  manageUsers: boolean;
  viewSystemMetrics: boolean;
  accessAdmin: boolean;
  viewSensitiveData: boolean;
  manageWorkflows: boolean;
  viewMCPTools: boolean;
  accessProcessingPipeline: boolean;
  configureWebhooks: boolean;
  viewAllDocuments: boolean;
}

const rolePermissions: Record<UserRole, Permission> = {
  admin: {
    viewAnalytics: true,
    viewAuditLogs: true,
    viewApiKeys: true,
    manageUsers: true,
    viewSystemMetrics: true,
    accessAdmin: true,
    viewSensitiveData: true,
    manageWorkflows: true,
    viewMCPTools: true,
    accessProcessingPipeline: true,
    configureWebhooks: true,
    viewAllDocuments: true,
  },
  developer: {
    viewAnalytics: true,
    viewAuditLogs: true,
    viewApiKeys: true,
    manageUsers: false,
    viewSystemMetrics: true,
    accessAdmin: false,
    viewSensitiveData: true,
    manageWorkflows: true,
    viewMCPTools: true,
    accessProcessingPipeline: true,
    configureWebhooks: true,
    viewAllDocuments: false,
  },
  user: {
    viewAnalytics: false,
    viewAuditLogs: false,
    viewApiKeys: false,
    manageUsers: false,
    viewSystemMetrics: false,
    accessAdmin: false,
    viewSensitiveData: false,
    manageWorkflows: false,
    viewMCPTools: false,
    accessProcessingPipeline: false,
    configureWebhooks: false,
    viewAllDocuments: false,
  },
};

export function getPermissions(role: UserRole): Permission {
  return rolePermissions[role];
}

export function hasPermission(role: UserRole, permission: keyof Permission): boolean {
  return rolePermissions[role][permission];
}

export function isAdmin(role: UserRole): boolean {
  return role === 'admin';
}

export function isDeveloper(role: UserRole): boolean {
  return role === 'developer';
}

export function isUser(role: UserRole): boolean {
  return role === 'user';
}

export function canAccessRoute(role: UserRole, route: string): boolean {
  const permissions = getPermissions(role);
  
  const routePermissions: Record<string, keyof Permission> = {
    '/admin': 'accessAdmin',
    '/analytics': 'viewAnalytics',
    '/audit-logs': 'viewAuditLogs',
    '/api-keys': 'viewApiKeys',
    '/workflows': 'manageWorkflows',
    '/mcp-tools': 'viewMCPTools',
    '/processing-pipeline': 'accessProcessingPipeline',
    '/webhooks': 'configureWebhooks',
  };
  
  const requiredPermission = routePermissions[route];
  if (!requiredPermission) {
    // Routes not in the map are accessible to all
    return true;
  }
  
  return permissions[requiredPermission];
}

export function maskSensitiveData(data: string, role: UserRole): string {
  if (hasPermission(role, 'viewSensitiveData')) {
    return data;
  }
  
  // Mask sensitive data for non-privileged users
  if (data.length <= 4) {
    return '***';
  }
  
  return data.substring(0, 4) + '*'.repeat(data.length - 4);
}

export function shouldShowField(fieldName: string, role: UserRole): boolean {
  const sensitiveFields = [
    'api_key',
    'secret',
    'password',
    'token',
    'connection_string',
    'database_url',
    'cost',
    'pricing',
    'internal_id',
  ];
  
  if (!hasPermission(role, 'viewSensitiveData')) {
    return !sensitiveFields.some(field => fieldName.toLowerCase().includes(field));
  }
  
  return true;
}

