export const ROLES = Object.freeze({
  USER: "user",
  ADMIN: "admin",
  SUPER_ADMIN: "super_admin",
});

export const ADMIN_ROLES = Object.freeze([ROLES.ADMIN, ROLES.SUPER_ADMIN]);

export const ROLE_HIERARCHY = Object.freeze({
  [ROLES.USER]: 1,
  [ROLES.ADMIN]: 5,
  [ROLES.SUPER_ADMIN]: 10,
});
