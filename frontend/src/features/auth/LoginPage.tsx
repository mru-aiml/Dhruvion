import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, Sparkles, Triangle } from "lucide-react";
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

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: { pathname: string } } };
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const validateEmail = (value: string) => {
    if (!value) return "Email is required";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return "Enter a valid email address";
    return null;
  };

  const validatePassword = (value: string) => {
    if (!value) return "Password is required";
    if (value.length < 8) return "Password must be at least 8 characters";
    return null;
  };

  const handleEmailBlur = () => setEmailError(validateEmail(email));
  const handlePasswordBlur = () => setPasswordError(validatePassword(password));

  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (emailError) setEmailError(validateEmail(value));
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    if (passwordError) setPasswordError(validatePassword(value));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password);

    if (emailErr || passwordErr) {
      setEmailError(emailErr);
      setPasswordError(passwordErr);
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      const dest = location.state?.from?.pathname ?? "/overview";
      navigate(dest, { replace: true });
    } catch (err: any) {
      const responseData = err?.response?.data;
      let message = "Incorrect email or password. Please try again.";

      // Handle standardized error response format: { error: { code, message, details }, request_id }
      if (responseData?.error) {
        const { code, message: errMessage } = responseData.error;
        if (code === "HTTP_ERROR" && errMessage?.includes("credentials")) {
          message = "Incorrect email or password. Please try again.";
        } else if (code === "HTTP_ERROR") {
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

  return (
    <div className="relative flex min-h-screen w-full bg-canvas overflow-hidden">
      <AuthLeftPanel />

      <AuthRightPanel>
        <MobileBackLink />

        <AuthCard>
          <AuthHeader
            title="Sign In"
            description="Access mission control for Alpha-1"
          />

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="text-micro text-text-muted block mb-1.5">
                Email
              </label>
              <div className="relative">
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
            </div>

            {/* Password Field */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="password" className="text-micro text-text-muted">
                  Password
                </label>
                <Link
                  to="#"
                  className="text-[10px] underline underline-offset-2 text-mars-orange hover:text-amber transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <TextInput
                  id="password"
                  type={showPw ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => handlePasswordChange(e.target.value)}
                  onBlur={handlePasswordBlur}
                  placeholder="Enter your password"
                  aria-invalid={passwordError ? "true" : "false"}
                  aria-describedby={passwordError ? "password-error" : undefined}
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
              {loading ? "Signing in…" : "Sign In"}
            </Button>
          </form>

          <Divider />

          {/* Create Account Link */}
          <AuthFooter className="text-center">
            <Button
              type="button"
              variant="outline"
              size="md"
              className="w-full"
              onClick={() => navigate("/signup")}
            >
              Create Account
            </Button>
          </AuthFooter>

          {/* Demo Credentials Hint */}
          <details className="mt-6">
            <summary className="flex items-center justify-center gap-1.5 text-[10px] uppercase tracking-[0.08em] text-text-muted/70 cursor-pointer">
              <Sparkles size={12} className="text-amber/60" aria-hidden />
              Demo credentials
            </summary>
            <div className="mt-3 p-3 rounded-control border border-line/40 bg-surface1/50 text-[10px] text-text-secondary">
              <p className="font-mono">demo@dhruvion.io</p>
              <p className="font-mono mt-1">Mission2026!</p>
            </div>
          </details>

          <BackLink />
        </AuthCard>
      </AuthRightPanel>
    </div>
  );
}