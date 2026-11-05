import { Navigate } from "react-router-dom";
import { getStoredRole, homePathForRole, isAuthenticated } from "../services/authApi";

/** Redirect to /login when JWT is missing; optionally require specific roles. */
export default function RequireAuth({ children, roles }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (Array.isArray(roles) && roles.length > 0) {
    const role = getStoredRole();
    if (!roles.includes(role)) {
      return <Navigate to={homePathForRole(role)} replace />;
    }
  }

  return children;
}
