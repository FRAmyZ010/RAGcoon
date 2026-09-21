import { Navigate } from "react-router-dom";
import { isAuthenticated } from "../services/authApi";

/** Redirect to /login when Administrator JWT is missing. */
export default function RequireAuth({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
