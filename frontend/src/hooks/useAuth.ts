import { useState, useCallback } from "react";
import { useNavigate } from "react-router";

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => !!localStorage.getItem("token"),
  );
  const navigate = useNavigate();

  const login = useCallback(
    (token: string) => {
      localStorage.setItem("token", token);
      setIsAuthenticated(true);
      navigate("/");
    },
    [navigate],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setIsAuthenticated(false);
    navigate("/login");
  }, [navigate]);

  return { isAuthenticated, login, logout };
}
