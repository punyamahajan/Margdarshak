import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  apiClient,
  type AuthResponse,
  type LoginPayload,
  type SignupPayload,
  type StudentProfile,
  type UpdateProfilePayload,
} from "../services/apiClient";

type AuthContextType = {
  student: StudentProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  signup: (payload: SignupPayload) => Promise<void>;
  updateProfile: (payload: UpdateProfilePayload) => Promise<StudentProfile>;
  logout: () => void;
  openAuthModal: (mode?: "login" | "signup") => void;
  closeAuthModal: () => void;
  authModalOpen: boolean;
  authModalMode: "login" | "signup";
  profileModalOpen: boolean;
  openProfileModal: () => void;
  closeProfileModal: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = "margdarshak_auth_token";
const STUDENT_STORAGE_KEY = "margdarshak_student_profile";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [student, setStudent] = useState<StudentProfile | null>(() => {
    const cached = localStorage.getItem(STUDENT_STORAGE_KEY);
    if (!cached) return null;
    try {
      return JSON.parse(cached) as StudentProfile;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<"login" | "signup">("login");
  const [profileModalOpen, setProfileModalOpen] = useState<boolean>(false);

  const openAuthModal = useCallback((mode: "login" | "signup" = "login") => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  }, []);

  const closeAuthModal = useCallback(() => {
    setAuthModalOpen(false);
  }, []);

  const openProfileModal = useCallback(() => {
    setProfileModalOpen(true);
  }, []);

  const closeProfileModal = useCallback(() => {
    setProfileModalOpen(false);
  }, []);

  // Verify and refresh profile from backend on mount if token exists
  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    apiClient
      .getMyProfile()
      .then((profile) => {
        setStudent(profile);
        localStorage.setItem(STUDENT_STORAGE_KEY, JSON.stringify(profile));
      })
      .catch(() => {
        // If token invalid, clear
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        localStorage.removeItem(STUDENT_STORAGE_KEY);
        setToken(null);
        setStudent(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  const handleAuthSuccess = (data: AuthResponse) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
    localStorage.setItem(STUDENT_STORAGE_KEY, JSON.stringify(data.student));
    setToken(data.access_token);
    setStudent(data.student);
    setAuthModalOpen(false);
  };

  const login = async (payload: LoginPayload) => {
    const response = await apiClient.login(payload);
    handleAuthSuccess(response);
  };

  const signup = async (payload: SignupPayload) => {
    const response = await apiClient.signup(payload);
    handleAuthSuccess(response);
  };

  const updateProfile = async (payload: UpdateProfilePayload): Promise<StudentProfile> => {
    const updated = await apiClient.updateProfile(payload);
    setStudent(updated);
    localStorage.setItem(STUDENT_STORAGE_KEY, JSON.stringify(updated));
    return updated;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(STUDENT_STORAGE_KEY);
    setToken(null);
    setStudent(null);
  };

  return (
    <AuthContext.Provider
      value={{
        student,
        token,
        isLoading,
        login,
        signup,
        updateProfile,
        logout,
        openAuthModal,
        closeAuthModal,
        authModalOpen,
        authModalMode,
        profileModalOpen,
        openProfileModal,
        closeProfileModal,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
