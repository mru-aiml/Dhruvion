import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, Triangle, CheckCircle2 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import Button from "../../components/common/Button";
import { TextInput } from "../../components/common/Field";
import {
  AuthLeftPanel,
  AuthRightPanel,
  AuthCard,
  AuthHeader,
  AuthFooter,
  Divider,
  BackLink,
  MobileBackLink,
} from "./AuthLayout";

export default function SignupPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fullNameError, setFullNameError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const validateFullName = (value: string) => {
    if (!value.trim()) return "Full name is required";
    if (value.trim().length < 2) return "Name must be at least 2 characters";
    return null;
  };

  const validateEmail = (value: string) => {
    if (!value) return "Email is required";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return "Enter a valid email address";
    return null;
  };

  const validatePassword = (value: string) => {
    if (!value) return "Password is required";
    if (value.length < 8) return "Password must be at least 8 characters";
    if (!/[A-Z]/.test(value)) return "Include at least one uppercase letter";
    if (!/[a-z]/.test(value)) return "Include at least one lowercase letter";
    if (!/[0-9]/.test(value)) return "Include at least one number";
    if (!/[^A-Za-z0-9]/.test(value)) return "Include at least one special character";
    return null;
  };

  const validateConfirm = (value: string) => {
    if (!value) return "Please confirm your password";
    if (value !== password) return "Passwords do not match";
    return null;
  };

  const handleFullNameBlur = () => setFullNameError(validateFullName(fullName));
  const handleEmailBlur = () => setEmailError(validateEmail(email));
  const handlePasswordBlur = () => setPasswordError(validatePassword(password));
  const handleConfirmBlur = () => setConfirmError(validateConfirm(confirm));

  const handleFullNameChange = (value: string) => {
    setFullName(value);
    if (fullNameError) setFullNameError(validateFullName(value));
  };

  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (emailError) setEmailError(validateEmail(value));
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    if (passwordError) setPasswordError(validatePassword(value));
    if (confirmError) setConfirmError(validateConfirm(confirm));
  };

  const handleConfirmChange = (value: string) => {
    setConfirm(value);
    if (confirmError) setConfirmError(validateConfirm(value));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const fullNameErr = validateFullName(fullName);
    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password);
    const confirmErr = validateConfirm(confirm);

    if (fullNameErr || emailErr || passwordErr || confirmErr) {
      setFullNameError(fullNameErr);
      setEmailError(emailErr);
      setPasswordError(passwordErr);
      setConfirmError(confirmErr);
      return;
    }

    setLoading(true);
    try {
      await register(fullName.trim(), email, password);
      navigate("/overview", { replace: true });
    } catch (err: any) {
      const responseData = err?.response?.data;
      let message = "Registration failed. Please try again.";

      // Handle standardized error response format: { error: { code, message, details }, request_id }
      if (responseData?.error) {
        const { code, message: errMessage } = responseData.error;
        if (err?.response?.status === 409) {
          // Conflict: duplicate email
          if (code === "HTTP_ERROR" && errMessage?.includes("Email")) {
            message = "An account with this email already exists. Please sign in.";
          } else if (code === "HTTP_ERROR" && errMessage?.includes("username")) {
            message = "This username is already taken.";
          } else {
            message = "An account with this information already exists. Please sign in.";
          }
        } else if (code === "INVALID_INPUT" || code === "HTTP_ERROR") {
          // Validation errors
          message = errMessage || message;
        } else {
          message = errMessage || message;
        }
      } else if (Array.isArray(responseData?.detail)) {
        // FastAPI validation error array
        message = responseData.detail.map((d: any) => d?.msg ?? JSON.stringify(d)).join("; ");
      } else if (typeof responseData?.detail === "string") {
        // Plain string detail
        message = responseData.detail;
      } else if (responseData?.detail?.message) {
        message = responseData.detail.message;
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const passwordStrength = (() => {
    if (!password) return 0;
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
  })();

  const strengthLabel = ["Very weak", "Weak", "Fair", "Good", "Strong"];
  const strengthColor = ["critical-red", "critical-red", "warning-amber", "cyan", "safe-green"];

  const hasMinLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);

  return (
    <div className="relative flex min-h-screen w-full bg-canvas overflow-hidden">
      <AuthLeftPanel />

      <AuthRightPanel>
        <MobileBackLink />

        <AuthCard>
          <AuthHeader
            title="Create Account"
            description="Join the mission control team"
          />

          <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
            {/* Full Name Field */}
            <div>
              <label htmlFor="fullName" className="text-micro text-text-muted block mb-1.5">
                Full name
              </label>
              <TextInput
                id="fullName"
                autoComplete="name"
                value={fullName}
                onChange={(e) => handleFullNameChange(e.target.value)}
                onBlur={handleFullNameBlur}
                placeholder="Enter your full name"
                aria-invalid={fullNameError ? "true" : "false"}
                aria-describedby={fullNameError ? "fullname-error" : undefined}
                className={fullNameError ? "border-critical-red/60" : ""}
              />
              {fullNameError && (
                <p id="fullname-error" className="mt-1.5 text-[11px] text-critical-red" role="alert">
                  {fullNameError}
                </p>
              )}
            </div>

            {/* Email Field */}
            <div>
              <label htmlFor="email" className="text-micro text-text-muted block mb-1.5">
                Email
              </label>
              <TextInput
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => handleEmailChange(e.target.value)}
                onBlur={handleEmailBlur}
                placeholder="you@example.com"
                aria-invalid={emailError ? "true" : "false"}
                aria-describedby={emailError ? "email-error" : undefined}
                className={emailError ? "border-critical-red/60" : ""}
              />
              {emailError && (
                <p id="email-error" className="mt-1.5 text-[11px] text-critical-red" role="alert">
                  {emailError}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="text-micro text-text-muted block mb-1.5">
                Password
              </label>
              <div className="relative">
                <TextInput
                  id="password"
                  type={showPw ? "text" : "password"}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => handlePasswordChange(e.target.value)}
                  onBlur={handlePasswordBlur}
                  placeholder="Create a secure password"
                  aria-invalid={passwordError ? "true" : "false"}
                  aria-describedby={passwordError ? "password-error" : "password-hint"}
                  className={passwordError ? "border-critical-red/60 pr-12" : "pr-12"}
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                  aria-label={showPw ? "Hide password" : "Show password"}
                  aria-pressed={showPw}
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
                {passwordError && (
                  <p id="password-error" className="mt-1.5 text-[11px] text-critical-red" role="alert">
                    {passwordError}
                  </p>
                )}
              </div>

              {/* Password Strength Indicator */}
              {password && (
                <div className="mt-2" role="progressbar" aria-valuenow={passwordStrength} aria-valuemin={0} aria-valuemax={5} aria-label="Password strength">
                  <div className="flex items-center gap-1.5">
                    <div className="flex-1 h-1.5 overflow-hidden rounded-full bg-surface3">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{
                          width: `${(passwordStrength / 5) * 100}%`,
                          backgroundColor: `var(--color-${strengthColor[passwordStrength - 1] || "critical-red"})`,
                        }}
                      />
                    </div>
                    <span className="text-[9px] uppercase tracking-[0.08em] text-text-muted shrink-0 w-24 text-right">
                      {strengthLabel[passwordStrength - 1] || "Very weak"}
                    </span>
                  </div>
                </div>
              )}

              {/* Password Requirements - Compact */}
              {password && (
                <ul className="mt-2 flex flex-wrap gap-2 text-[10px] text-text-muted" aria-label="Password requirements" role="list">
                  <li className={`flex items-center gap-1 ${hasMinLength ? "text-safe-green" : "text-text-muted/40"}`}>
                    <CheckCircle2 size={10} className="shrink-0" aria-hidden />
                    8+ chars
                  </li>
                  <li className={`flex items-center gap-1 ${hasUpper ? "text-safe-green" : "text-text-muted/40"}`}>
                    <CheckCircle2 size={10} className="shrink-0" aria-hidden />
                    Uppercase
                  </li>
                  <li className={`flex items-center gap-1 ${hasLower ? "text-safe-green" : "text-text-muted/40"}`}>
                    <CheckCircle2 size={10} className="shrink-0" aria-hidden />
                    Lowercase
                  </li>
                  <li className={`flex items-center gap-1 ${hasNumber ? "text-safe-green" : "text-text-muted/40"}`}>
                    <CheckCircle2 size={10} className="shrink-0" aria-hidden />
                    Number
                  </li>
                  <li className={`flex items-center gap-1 ${hasSpecial ? "text-safe-green" : "text-text-muted/40"}`}>
                    <CheckCircle2 size={10} className="shrink-0" aria-hidden />
                    Special
                  </li>
                </ul>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <label htmlFor="confirm" className="text-micro text-text-muted block mb-1.5">
                Confirm password
              </label>
              <div className="relative">
                <TextInput
                  id="confirm"
                  type={showPw ? "text" : "password"}
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => handleConfirmChange(e.target.value)}
                  onBlur={handleConfirmBlur}
                  placeholder="Confirm your password"
                  aria-invalid={confirmError ? "true" : "false"}
                  aria-describedby={confirmError ? "confirm-error" : undefined}
                  className={confirmError ? "border-critical-red/60 pr-12" : "pr-12"}
                />
                {confirmError && (
                  <p id="confirm-error" className="mt-1.5 text-[11px] text-critical-red" role="alert">
                    {confirmError}
                  </p>
                )}
                {confirm && !confirmError && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[10px] text-safe-green">
                    <CheckCircle2 size={10} aria-hidden />
                    Match
                  </div>
                )}
              </div>
            </div>

            {/* Global Error */}
            {error && (
              <div
                className="rounded-control border border-critical-red/40 bg-critical-red/[0.07] p-3"
                role="alert"
              >
                <div className="flex items-start gap-2">
                  <Triangle size={14} className="mt-0.5 shrink-0 text-critical-red" aria-hidden />
                  <p className="text-[11px] leading-relaxed text-text-secondary">{error}</p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              loading={loading}
              icon={!loading ? <Loader2 size={14} /> : undefined}
            >
              {loading ? "Creating account…" : "Create Account"}
            </Button>
          </form>

          <Divider />

          {/* Sign In Link */}
          <AuthFooter className="text-center">
            <Button
              type="button"
              variant="outline"
              size="md"
              className="w-full"
              onClick={() => navigate("/login")}
            >
              Sign In
            </Button>
          </AuthFooter>

          {/* Terms */}
          <p className="mt-5 text-center text-[10px] leading-relaxed text-text-muted">
            By creating an account, you agree to the{" "}
            <Link to="#" className="text-mars-orange hover:underline">Mission Terms</Link>
            {" and "}
            <Link to="#" className="text-mars-orange hover:underline">Data Policy</Link>
            {". Demo environment only."}
          </p>

          <BackLink />
        </AuthCard>
      </AuthRightPanel>
    </div>
  );
}